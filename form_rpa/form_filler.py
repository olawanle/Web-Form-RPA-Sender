from __future__ import annotations

import re
import random
import time
from datetime import datetime
from typing import Dict, Optional, Tuple, List

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException


FIELD_HINTS = {
	"name": [
		"name", "your-name", "fullname", "full-name", "contact",
		"お名前", "氏名", "担当者", "担当者名", "ご担当者",
	],
	"company": [
		"company", "organization", "corp", "company-name",
		"会社名", "御社名", "貴社名", "法人名", "店舗名",
	],
	"email": [
		"email", "mail", "e-mail", "your-email",
		"メール", "メールアドレス",
	],
	"phone": [
		"phone", "tel", "telephone",
		"携帯", "電話", "電話番号",
	],
	"subject": [
		"subject",
		"件名", "題名",
	],
	"message": [
		"message", "inquiry", "contact", "body", "comment",
		"お問い合わせ", "お問い合わせ内容", "内容", "本文", "ご用件", "ご質問",
	],
}

SUBMIT_HINTS = [
	"submit", "send", "送信", "確認", "confirm", "お問い合わせ送信", "確定"
]

CONSENT_HINTS = [
	"同意", "プライバシー", "個人情報", "利用規約", "規約", "個人情報の取り扱い", "個人情報保護方針",
]

ERROR_HINTS_REQUIRED = [
	"必須", "必須項目", "入力してください", "未入力", "required", "is required",
]

CONTACT_LINK_HINTS = [
	"お問い合わせ", "お問合せ", "問合せ", "コンタクト", "資料請求", "お見積り", "contact", "inquiry"
]

COOKIE_BUTTON_HINTS = [
	"同意", "許可", "同意する", "同意して続行", "Accept", "I agree", "許可する", "同意して受け入れる"
]


def detect_required_errors(driver: WebDriver) -> bool:
	page = driver.page_source
	low = page.lower()
	if any(h in page for h in ERROR_HINTS_REQUIRED) or any(h in low for h in ["required", "please enter"]):
		return True
	try:
		invalid_count = driver.execute_script("return document.querySelectorAll(':invalid').length")
		return bool(invalid_count and invalid_count > 0)
	except Exception:
		return False


def collect_required_fields(driver: WebDriver) -> List[Dict[str, str]]:
	fields: List[Dict[str, str]] = []
	candidates = driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")
	for el in candidates:
		try:
			required = _is_required(el)
			if not required:
				continue
			key = (el.get_attribute("name") or el.get_attribute("id") or "field")
			item = {
				"key": key,
				"label": "",
				"placeholder": el.get_attribute("placeholder") or "",
				"name": el.get_attribute("name") or "",
				"id": el.get_attribute("id") or "",
				"type": el.get_attribute("type") or el.tag_name,
			}
			try:
				label = el.find_element(By.XPATH, "ancestor::label")
				if label.text:
					item["label"] = label.text.strip()
			except Exception:
				pass
			fid = el.get_attribute("id")
			if fid:
				labels = driver.find_elements(By.CSS_SELECTOR, f"label[for='{fid}']")
				for lb in labels:
					if lb.text:
						item["label"] = lb.text.strip()
			fields.append(item)
		except Exception:
			continue
	return fields


def _is_required(el) -> bool:
	req = (el.get_attribute("required") or "").lower()
	aria = (el.get_attribute("aria-required") or "").lower()
	classes = (el.get_attribute("class") or "").lower()
	return req == "true" or aria == "true" or "required" in classes


def _dispatch_set_value(driver: WebDriver, element, value: str) -> None:
	# Set value and dispatch input/change for React/Vue-controlled inputs
	try:
		driver.execute_script(
			"""
			const el = arguments[0];
			const val = arguments[1];
			if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
				el.focus();
				el.value = val;
				el.dispatchEvent(new Event('input', { bubbles: true }));
				el.dispatchEvent(new Event('change', { bubbles: true }));
			} else {
				try { el.value = val; } catch (e) {}
			}
			""",
			element,
			value,
		)
	except Exception:
		pass


def _label_text_for_element(driver: WebDriver, el) -> str:
	texts: List[str] = []
	try:
		label_ancestor = el.find_element(By.XPATH, "ancestor::label")
		if label_ancestor.text:
			texts.append(label_ancestor.text.strip())
	except Exception:
		pass
	fid = el.get_attribute("id") or ""
	if fid:
		for lb in driver.find_elements(By.CSS_SELECTOR, f"label[for='{fid}']"):
			if lb.text:
				texts.append(lb.text.strip())
	return " ".join(texts)


def _checkbox_set_checked(driver: WebDriver, el) -> bool:
	try:
		if not el.is_selected():
			try:
				driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
				el.click()
				return True
			except Exception:
				pass
			# Try clicking label
			fid = el.get_attribute("id") or ""
			if fid:
				for lb in driver.find_elements(By.CSS_SELECTOR, f"label[for='{fid}']"):
					try:
						driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", lb)
						lb.click()
						if el.is_selected():
							return True
					except Exception:
						continue
			# Fallback to JS set + events
		driver.execute_script(
			"""
			const el = arguments[0];
			if (!el.checked) {
				el.checked = true;
				el.dispatchEvent(new Event('click', { bubbles: true }));
				el.dispatchEvent(new Event('change', { bubbles: true }));
			}
			""",
			el,
		)
		return True
	except Exception:
		return False


def accept_consents(driver: WebDriver, auto_consent: bool) -> int:
	if not auto_consent:
		return 0
	accepted = 0
	labels = driver.find_elements(By.TAG_NAME, "label")
	for label in labels:
		text = (label.text or "")
		if not text:
			continue
		low = text.lower()
		if any(h in text for h in CONSENT_HINTS) or any(h in low for h in ["privacy", "policy", "terms", "agree"]):
			for_attr = label.get_attribute("for")
			if for_attr:
				try:
					cb = driver.find_element(By.ID, for_attr)
					if cb.get_attribute("type") == "checkbox" and not cb.is_selected():
						if _checkbox_set_checked(driver, cb):
							accepted += 1
				except Exception:
					continue
	# Fallback: unchecked consent-like checkboxes without labels
	cbs = driver.find_elements(By.CSS_SELECTOR, "input[type=checkbox]")
	for cb in cbs:
		if cb.is_selected():
			continue
		name = (cb.get_attribute("name") or "")
		id_attr = (cb.get_attribute("id") or "")
		aria = (cb.get_attribute("aria-label") or "")
		meta = f"{name} {id_attr} {aria} {_label_text_for_element(driver, cb)}"
		low = meta.lower()
		if any(h in meta for h in CONSENT_HINTS) or any(k in low for k in ["privacy", "terms", "agree", "policy"]):
			if _checkbox_set_checked(driver, cb):
				accepted += 1
	return accepted


def click_cookie_banners(driver: WebDriver) -> int:
	clicked = 0
	for sel in ["button", "[role=button]", "a"]:
		for el in driver.find_elements(By.CSS_SELECTOR, sel):
			text = (el.text or "").strip()
			low = text.lower()
			if any(h in text for h in COOKIE_BUTTON_HINTS) or any(k in low for k in ["accept", "agree", "consent"]):
				try:
					driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
					el.click()
					clicked += 1
				except Exception:
					continue
	return clicked


def click_contact_entry_link(driver: WebDriver) -> bool:
	links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
	for a in links:
		text = (a.text or "").strip()
		low = text.lower()
		if any(h in text for h in CONTACT_LINK_HINTS) or any(k in low for k in ["contact", "inquiry"]):
			try:
				a.click()
				return True
			except Exception:
				continue
	return False


def _find_by_label_association(driver: WebDriver, keywords: List[str]):
	labels = driver.find_elements(By.TAG_NAME, "label")
	for label in labels:
		text = (label.text or "").strip().lower()
		if any(k in text for k in keywords):
			for_attr = label.get_attribute("for")
			if for_attr:
				try:
					return driver.find_element(By.ID, for_attr)
				except NoSuchElementException:
					pass
	return None


def _find_input_like(driver: WebDriver, keywords: List[str], input_types=("text", "email", "tel")):
	kw = [k.lower() for k in keywords]
	el = _find_by_label_association(driver, kw)
	if el is not None:
		return el
	candidates = driver.find_elements(By.CSS_SELECTOR, "input, textarea")
	for el in candidates:
		tag = el.tag_name.lower()
		attr_text = " ".join([
			(el.get_attribute("name") or ""),
			(el.get_attribute("id") or ""),
			(el.get_attribute("placeholder") or ""),
			(el.get_attribute("aria-label") or ""),
		]).lower()
		if tag == "input":
			input_type = (el.get_attribute("type") or "text").lower()
			if input_type not in input_types and not any(k in attr_text for k in kw):
				continue
		if any(k in attr_text for k in kw):
			return el
	return None


def _find_selects(driver: WebDriver) -> List[Select]:
	select_els = driver.find_elements(By.TAG_NAME, "select")
	selects: List[Select] = []
	for el in select_els:
		try:
			selects.append(Select(el))
		except Exception:
			continue
	return selects


def _choose_select_option(select: Select) -> bool:
	try:
		options = select.options
		for opt in options:
			text = (opt.text or "").strip()
			val = (opt.get_attribute("value") or "").strip()
			if text and val:
				select.select_by_value(val)
				return True
	except Exception:
		return False
	return False


def _choose_first_radio_in_group(driver: WebDriver, input_el) -> bool:
	name = input_el.get_attribute("name") or ""
	if not name:
		return False
	group = driver.find_elements(By.CSS_SELECTOR, f"input[type=radio][name='{name}']")
	for el in group:
		try:
			el.click()
			return True
		except Exception:
			continue
	return False


def switch_into_form_iframe_if_any(driver: WebDriver) -> bool:
	iframes = driver.find_elements(By.TAG_NAME, "iframe")
	for i, frame in enumerate(iframes):
		try:
			driver.switch_to.frame(frame)
			# Form detectable?
			if driver.find_elements(By.CSS_SELECTOR, "input, textarea, select"):
				return True
			# Not a form iframe, go back
			driver.switch_to.default_content()
		except Exception:
			try:
				driver.switch_to.default_content()
			except Exception:
				pass
	return False


def find_fields(driver: WebDriver) -> Dict[str, Optional[object]]:
	fields = {
		"name": _find_input_like(driver, FIELD_HINTS["name"], input_types=("text")),
		"company": _find_input_like(driver, FIELD_HINTS["company"], input_types=("text")),
		"email": _find_input_like(driver, FIELD_HINTS["email"], input_types=("email", "text")),
		"phone": _find_input_like(driver, FIELD_HINTS["phone"], input_types=("tel", "text")),
		"subject": _find_input_like(driver, FIELD_HINTS["subject"], input_types=("text")),
		"message": _find_input_like(driver, FIELD_HINTS["message"], input_types=("text")),
	}
	return fields


def fill_fields(driver: WebDriver, values: Dict[str, str], *, auto_selects: bool = True, auto_radios: bool = True, auto_consent: bool = False) -> Dict[str, bool]:
	# Try entering into a form iframe if present
	switched = switch_into_form_iframe_if_any(driver)
	fields = find_fields(driver)
	result = {}
	for key, element in fields.items():
		filled = False
		value = values.get(key, "").strip()
		if element is not None and value:
			try:
				element.clear()
				element.send_keys(value)
				_dispatch_set_value(driver, element, value)
				filled = True
			except Exception:
				try:
					_dispatch_set_value(driver, element, value)
					filled = True
				except Exception:
					filled = False
		result[key] = filled

	if auto_selects:
		for select in _find_selects(driver):
			el = select._el
			if _is_required(el):
				_choose_select_option(select)
	if auto_radios:
		radios = driver.find_elements(By.CSS_SELECTOR, "input[type=radio]")
		for r in radios:
			if _is_required(r):
				_choose_first_radio_in_group(driver, r)

	accept_consents(driver, auto_consent=auto_consent)
	# Exit iframe to restore context
	if switched:
		try:
			driver.switch_to.default_content()
		except Exception:
			pass
	return result


def _elements_with_text(driver: WebDriver, selector: str, hints: List[str]):
	matches = []
	for el in driver.find_elements(By.CSS_SELECTOR, selector):
		text = ((el.text or "") + " " + (el.get_attribute("value") or "")).strip().lower()
		if any(h in text for h in hints):
			matches.append(el)
	return matches


def _submit_enclosing_form(driver: WebDriver) -> bool:
	forms = driver.find_elements(By.TAG_NAME, "form")
	if len(forms) == 1:
		try:
			driver.execute_script("arguments[0].submit();", forms[0])
			return True
		except Exception:
			pass
	fields = find_fields(driver)
	candidates = [el for el in fields.values() if el is not None]
	for el in candidates:
		try:
			form = el.find_element(By.XPATH, "ancestor::form")
			driver.execute_script("arguments[0].submit();", form)
			return True
		except Exception:
			continue
	return False


def click_submit(driver: WebDriver) -> bool:
	selector_sets = [
		("button[type=submit], input[type=submit]", SUBMIT_HINTS),
		("button, input[type=button]", SUBMIT_HINTS),
		("[role=button]", SUBMIT_HINTS),
		("a", SUBMIT_HINTS),
	]
	for selector, hints in selector_sets:
		for el in _elements_with_text(driver, selector, [h.lower() for h in hints]):
			try:
				driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
				el.click()
				return True
			except Exception:
				continue
	if _submit_enclosing_form(driver):
		return True
	return False


def multi_step_submit(driver: WebDriver, timeout_first: int = 6, timeout_second: int = 6) -> bool:
	clicked = click_submit(driver)
	if not clicked:
		return False
	try:
		WebDriverWait(driver, timeout_first).until(
			lambda d: "確認" in d.page_source or "confirm" in d.page_source.lower() or "内容確認" in d.page_source
		)
		selector_sets = [
			("button[type=submit], input[type=submit]", ["送信", "submit", "確定", "send"]),
			("button, input[type=button]", ["送信", "確定", "send"]),
		]
		for selector, hints in selector_sets:
			for el in _elements_with_text(driver, selector, [h.lower() for h in hints]):
				try:
					driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
					el.click()
					return True
				except Exception:
					continue
	except TimeoutException:
		return True
	return False


def wait_post_submit(driver: WebDriver, timeout: int = 10) -> None:
	try:
		WebDriverWait(driver, timeout).until(
			lambda d: "thank" in d.page_source.lower() or "成功" in d.page_source or "受け付け" in d.page_source or "送信" in d.page_source
		)
	except TimeoutException:
		pass


def _infer_semantic(keywords: str, input_type: str, tag_name: str) -> str:
	low = keywords.lower()
	if any(k in low for k in ["mail", "email", "e-mail", "メール"]):
		return "email"
	if any(k in low for k in ["tel", "phone", "電話"]):
		return "phone"
	if any(k in low for k in ["zip", "postal", "郵便", "〒"]):
		return "zip"
	if any(k in low for k in ["addr", "住所", "所在地", "番地"]):
		return "address"
	if any(k in low for k in ["city", "市区町村"]):
		return "city"
	if any(k in low for k in ["pref", "都道府県", "県", "府", "都"]):
		return "prefecture"
	if any(k in low for k in ["company", "法人", "会社", "企業", "貴社", "御社", "店舗"]):
		return "company"
	if any(k in low for k in ["name", "氏名", "お名前", "担当"]):
		return "name"
	if any(k in low for k in ["subject", "件名", "題名"]):
		return "subject"
	if any(k in low for k in ["url", "website", "ウェブ", "サイト"]):
		return "url"
	if any(k in low for k in ["date", "日付", "年月日"]):
		return "date"
	if input_type in ["number", "range"]:
		return "number"
	if tag_name == "textarea":
		return "textarea"
	return "text"


def _placeholder_for_semantic(semantic: str) -> str:
	if semantic == "email":
		return "info@example.com"
	if semantic == "phone":
		return "050-1234-5678"
	if semantic == "zip":
		return "650-0001"
	if semantic == "address":
		return "兵庫県神戸市中央区サンプル1-2-3"
	if semantic == "city":
		return "神戸市"
	if semantic == "prefecture":
		return "兵庫県"
	if semantic == "company":
		return "株式会社サンプル"
	if semantic == "name":
		return "山田 太郎"
	if semantic == "subject":
		return "お問い合わせ"
	if semantic == "url":
		return "https://example.com"
	if semantic == "date":
		return datetime.now().strftime("%Y-%m-%d")
	if semantic == "number":
		return str(random.randint(1, 9))
	return "サンプル"


def _is_message_like(el) -> bool:
	meta = " ".join([
		(el.get_attribute("name") or ""),
		(el.get_attribute("id") or ""),
		(el.get_attribute("placeholder") or ""),
		(el.get_attribute("aria-label") or ""),
		el.tag_name or "",
	])
	low = meta.lower()
	if any(h.lower() in low for h in FIELD_HINTS["message"]):
		return True
	return el.tag_name.lower() == "textarea"


def auto_fill_remaining(driver: WebDriver, *, skip_message: bool = True) -> int:
	"""Fill all remaining empty or required fields with reasonable placeholders.
	Returns number of fields filled.
	"""
	filled = 0
	switched = switch_into_form_iframe_if_any(driver)
	# Fill inputs and textareas
	candidates = driver.find_elements(By.CSS_SELECTOR, "input, textarea")
	for el in candidates:
		try:
			input_type = (el.get_attribute("type") or "text").lower()
			tag = el.tag_name.lower()
			if tag == "input" and input_type in ["hidden", "file", "submit", "button", "image", "reset"]:
				continue
			if skip_message and _is_message_like(el):
				# preserve message content set by template
				continue
			current = (el.get_attribute("value") or "").strip()
			if current and not _is_required(el):
				continue
			keywords = " ".join([
				(el.get_attribute("name") or ""),
				(el.get_attribute("id") or ""),
				(el.get_attribute("placeholder") or ""),
				(el.get_attribute("aria-label") or ""),
			])
			semantic = _infer_semantic(keywords, input_type, tag)
			value = _placeholder_for_semantic(semantic)
			try:
				el.clear()
				el.send_keys(value)
				_dispatch_set_value(driver, el, value)
				filled += 1
			except Exception:
				try:
					_dispatch_set_value(driver, el, value)
					filled += 1
				except Exception:
					pass
		except Exception:
			continue
	# Selects
	for select in _find_selects(driver):
		try:
			_choose_select_option(select)
			filled += 1
		except Exception:
			continue
	# Radios: choose first in each group if required
	radios = driver.find_elements(By.CSS_SELECTOR, "input[type=radio]")
	seen_groups = set()
	for r in radios:
		name = r.get_attribute("name") or ""
		if name in seen_groups:
			continue
		seen_groups.add(name)
		if _is_required(r):
			if _choose_first_radio_in_group(driver, r):
				filled += 1
	# Checkboxes: required, and consent-like even if not marked required
	cbs = driver.find_elements(By.CSS_SELECTOR, "input[type=checkbox]")
	for cb in cbs:
		if cb.is_selected():
			continue
		required_flag = _is_required(cb)
		meta = f"{cb.get_attribute('name') or ''} {cb.get_attribute('id') or ''} {cb.get_attribute('aria-label') or ''} {_label_text_for_element(driver, cb)}"
		if required_flag or any(h in meta for h in CONSENT_HINTS):
			if _checkbox_set_checked(driver, cb):
				filled += 1
	if switched:
		try:
			driver.switch_to.default_content()
		except Exception:
			pass
	return filled
