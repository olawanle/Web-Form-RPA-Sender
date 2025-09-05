from __future__ import annotations

import re
import time
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
	# Try label association first
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


def _is_required(el) -> bool:
	req = (el.get_attribute("required") or "").lower()
	aria = (el.get_attribute("aria-required") or "").lower()
	classes = (el.get_attribute("class") or "").lower()
	return req == "true" or aria == "true" or "required" in classes


def _choose_select_option(select: Select) -> bool:
	# Choose first non-empty option if field is required and nothing is selected
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


def accept_consents(driver: WebDriver, auto_consent: bool) -> int:
	if not auto_consent:
		return 0
	accepted = 0
	# Click checkboxes with consent-related labels
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
						cb.click()
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
		meta = f"{name} {id_attr} {aria}"
		low = meta.lower()
		if any(h in meta for h in CONSENT_HINTS) or any(k in low for k in ["privacy", "terms", "agree", "policy"]):
			try:
				cb.click()
				accepted += 1
			except Exception:
				continue
	return accepted


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
	fields = find_fields(driver)
	result = {}
	for key, element in fields.items():
		filled = False
		value = values.get(key, "").strip()
		if element is not None and value:
			try:
				element.clear()
				element.send_keys(value)
				filled = True
			except Exception:
				filled = False
		result[key] = filled

	# Optionally choose selects/radios for required fields
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

	# Optionally accept consents
	accept_consents(driver, auto_consent=auto_consent)
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
	# First click
	clicked = click_submit(driver)
	if not clicked:
		return False
	try:
		WebDriverWait(driver, timeout_first).until(
			lambda d: "確認" in d.page_source or "confirm" in d.page_source.lower() or "内容確認" in d.page_source
		)
		# On confirm page, try to find final send
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
		# No explicit confirm step detected; rely on first click
		return True
	return False


def wait_post_submit(driver: WebDriver, timeout: int = 10) -> None:
	try:
		WebDriverWait(driver, timeout).until(
			lambda d: "thank" in d.page_source.lower() or "成功" in d.page_source or "受け付け" in d.page_source or "送信" in d.page_source
		)
	except TimeoutException:
		pass
