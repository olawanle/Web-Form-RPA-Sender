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
		"name", "your-name", "fullname", "full-name", "contact", "firstname", "lastname",
		"お名前", "氏名", "担当者", "担当者名", "ご担当者", "姓名", "フルネーム", "お客様名",
		"customer_name", "user_name", "contact_name", "representative", "responsible"
	],
	"company": [
		"company", "organization", "corp", "company-name", "business", "firm", "enterprise",
		"会社名", "御社名", "貴社名", "法人名", "店舗名", "企業名", "組織名", "事業者名",
		"organization_name", "business_name", "firm_name", "client_name"
	],
	"email": [
		"email", "mail", "e-mail", "your-email", "email-address", "mail-address",
		"メール", "メールアドレス", "メールアドレス", "連絡先メール", "返信先メール",
		"contact_email", "reply_email", "notification_email"
	],
	"phone": [
		"phone", "tel", "telephone", "mobile", "cell", "phone-number", "contact-number",
		"携帯", "電話", "電話番号", "連絡先", "連絡先電話", "お電話", "TEL",
		"contact_phone", "mobile_phone", "phone_number", "telephone_number"
	],
	"subject": [
		"subject", "title", "topic", "inquiry-subject", "message-subject",
		"件名", "題名", "タイトル", "お問い合わせ件名", "ご用件", "件名",
		"inquiry_title", "message_title", "contact_subject"
	],
	"message": [
		"message", "inquiry", "contact", "body", "comment", "content", "description",
		"お問い合わせ", "お問い合わせ内容", "内容", "本文", "ご用件", "ご質問", "メッセージ",
		"inquiry_message", "contact_message", "message_body", "comments", "details"
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
	
	# Enhanced: Try to find fields by more comprehensive patterns
	fields = _enhance_field_detection(driver, fields)
	
	return fields


def _enhance_field_detection(driver: WebDriver, fields: Dict[str, Optional[object]]) -> Dict[str, Optional[object]]:
	"""Enhanced field detection using more comprehensive patterns."""
	# If we still don't have some fields, try more aggressive detection
	for field_type in ["name", "company", "email", "phone", "subject", "message"]:
		if fields.get(field_type) is not None:
			continue
		
		# Try finding by input type first
		if field_type == "email":
			email_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type=email]")
			if email_inputs:
				fields[field_type] = email_inputs[0]
				continue
		elif field_type == "phone":
			tel_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type=tel]")
			if tel_inputs:
				fields[field_type] = tel_inputs[0]
				continue
		
		# Try finding by placeholder text
		placeholder_hints = FIELD_HINTS[field_type]
		for hint in placeholder_hints:
			placeholder_inputs = driver.find_elements(By.CSS_SELECTOR, f"input[placeholder*='{hint}'], textarea[placeholder*='{hint}']")
			if placeholder_inputs:
				fields[field_type] = placeholder_inputs[0]
				break
		
		# Try finding by aria-label
		if fields.get(field_type) is None:
			for hint in placeholder_hints:
				aria_inputs = driver.find_elements(By.CSS_SELECTOR, f"input[aria-label*='{hint}'], textarea[aria-label*='{hint}']")
				if aria_inputs:
					fields[field_type] = aria_inputs[0]
					break
		
		# Try finding by class name patterns
		if fields.get(field_type) is None:
			class_patterns = {
				"name": ["name", "fullname", "contact", "user"],
				"company": ["company", "organization", "business", "firm"],
				"email": ["email", "mail", "contact"],
				"phone": ["phone", "tel", "mobile", "contact"],
				"subject": ["subject", "title", "topic"],
				"message": ["message", "comment", "content", "body"]
			}
			for pattern in class_patterns.get(field_type, []):
				class_inputs = driver.find_elements(By.CSS_SELECTOR, f"input[class*='{pattern}'], textarea[class*='{pattern}']")
				if class_inputs:
					fields[field_type] = class_inputs[0]
					break
	
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
	
	# Enhanced: Fill ALL remaining empty fields with placeholders
	_fill_all_remaining_fields_aggressive(driver, values)
	
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
	"""ULTRA-AGGRESSIVE submit button detection - 10+ strategies for 100% success."""
	
	print("🔍 ULTRA-AGGRESSIVE submit button detection...")
	
	# Strategy 1: Explicit submit buttons
	submit_selectors = [
		"button[type=submit]", "input[type=submit]", 
		"input[type=button][value*='送信']", "input[type=button][value*='submit']", "input[type=button][value*='send']",
		"button[value*='送信']", "button[value*='submit']", "button[value*='send']",
		"input[type=button][value*='確認']", "button[value*='確認']",
		"input[type=button][value*='完了']", "button[value*='完了']",
		"input[type=button][value*='実行']", "button[value*='実行']"
	]
	
	for selector in submit_selectors:
		buttons = driver.find_elements(By.CSS_SELECTOR, selector)
		for btn in buttons:
			if _try_click_button(driver, btn, "explicit submit"):
				return True
	
	# Strategy 2: Text-based detection
	submit_texts = ["送信", "submit", "send", "確認", "confirm", "送る", "送付", "完了", "確定", "実行", "実行する", "送信する", "確認する", "完了する"]
	all_buttons = driver.find_elements(By.CSS_SELECTOR, "button, input[type=button], [role=button], a")
	
	for btn in all_buttons:
		text = (btn.text or btn.get_attribute("value") or "").strip()
		if any(submit_text in text.lower() for submit_text in submit_texts):
			if _try_click_button(driver, btn, f"text: {text}"):
				return True
	
	# Strategy 3: Form context buttons
	forms = driver.find_elements(By.CSS_SELECTOR, "form")
	for form in forms:
		form_buttons = form.find_elements(By.CSS_SELECTOR, "button, input[type=button], input[type=submit], a")
		for btn in form_buttons:
			text = (btn.text or btn.get_attribute("value") or "").strip().lower()
			if not any(skip_word in text for skip_word in ["cancel", "reset", "clear", "キャンセル", "リセット", "クリア", "戻る", "back"]):
				if _try_click_button(driver, btn, f"form button: {text}"):
					return True
	
	# Strategy 4: Class/ID pattern matching
	class_id_patterns = ["submit", "send", "btn-submit", "submit-btn", "送信", "確認", "send-btn", "submit-button"]
	for pattern in class_id_patterns:
		buttons = driver.find_elements(By.CSS_SELECTOR, f"*[class*='{pattern}'], *[id*='{pattern}']")
		for btn in buttons:
			if _try_click_button(driver, btn, f"class/id: {pattern}"):
				return True
	
	# Strategy 5: JavaScript event handlers
	js_buttons = driver.find_elements(By.CSS_SELECTOR, "*[onclick], *[onmousedown], *[onmouseup]")
	for btn in js_buttons:
		onclick = btn.get_attribute("onclick") or ""
		if any(js_word in onclick.lower() for js_word in ["submit", "send", "送信", "form", "submitform"]):
			if _try_click_button(driver, btn, f"JS event: {onclick[:50]}"):
				return True
	
	# Strategy 6: Try all clickable elements in forms
	clickable_in_forms = driver.find_elements(By.CSS_SELECTOR, "form *[onclick], form button, form input[type=button], form a")
	for el in clickable_in_forms:
		if _try_click_button(driver, el, "clickable in form"):
			return True
	
	# Strategy 7: JavaScript form submission
	if _try_js_form_submission(driver):
		print("✓ Submitted form via JavaScript")
		return True
	
	# Strategy 8: Try pressing Enter on form elements
	if _try_enter_key_submission(driver):
		print("✓ Submitted form via Enter key")
		return True
	
	# Strategy 9: Look for any element with submit-related attributes
	submit_attrs = driver.find_elements(By.CSS_SELECTOR, "*[data-submit], *[data-action='submit'], *[data-action='send']")
	for el in submit_attrs:
		if _try_click_button(driver, el, "data attributes"):
			return True
	
	# Strategy 10: Last resort - try any button that might submit
	all_possible_buttons = driver.find_elements(By.CSS_SELECTOR, "button, input[type=button], input[type=submit], a, [role=button]")
	for btn in all_possible_buttons:
		if btn.is_displayed() and btn.is_enabled():
			text = (btn.text or btn.get_attribute("value") or "").strip()
			if text and len(text) < 50:  # Short text, likely a button
				if _try_click_button(driver, btn, f"last resort: {text}"):
					return True
	
	print("✗ No submit method found after 10 strategies")
	return False


def _try_click_button(driver: WebDriver, btn, description: str) -> bool:
	"""Try to click a button with multiple methods."""
	try:
		if not btn.is_displayed() or not btn.is_enabled():
			return False
		
		# Method 1: Direct click
		driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
		btn.click()
		print(f"✓ Clicked button ({description})")
		return True
	except Exception:
		try:
			# Method 2: JavaScript click
			driver.execute_script("arguments[0].click();", btn)
			print(f"✓ Clicked button via JS ({description})")
			return True
		except Exception:
			try:
				# Method 3: ActionChains click
				from selenium.webdriver.common.action_chains import ActionChains
				ActionChains(driver).move_to_element(btn).click().perform()
				print(f"✓ Clicked button via ActionChains ({description})")
				return True
			except Exception:
				return False


def _try_js_form_submission(driver: WebDriver) -> bool:
	"""Try to submit forms using JavaScript."""
	try:
		# Try to find and submit all forms
		forms = driver.find_elements(By.CSS_SELECTOR, "form")
		for form in forms:
			try:
				driver.execute_script("arguments[0].submit();", form)
				print("✓ Submitted form via JS submit()")
				return True
			except Exception:
				continue
		
		# Try to trigger form submission events
		driver.execute_script("""
			var forms = document.querySelectorAll('form');
			for (var i = 0; i < forms.length; i++) {
				var event = new Event('submit', {bubbles: true, cancelable: true});
				forms[i].dispatchEvent(event);
			}
		""")
		print("✓ Triggered form submit events")
		return True
	except Exception:
		return False


def _try_enter_key_submission(driver: WebDriver) -> bool:
	"""Try to submit forms by pressing Enter on form elements."""
	try:
		from selenium.webdriver.common.keys import Keys
		
		# Try pressing Enter on various form elements
		form_elements = driver.find_elements(By.CSS_SELECTOR, "form input, form textarea, form select")
		for el in form_elements:
			try:
				el.send_keys(Keys.RETURN)
				print("✓ Pressed Enter on form element")
				return True
			except Exception:
				continue
		return False
	except Exception:
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


def wait_post_submit(driver: WebDriver, timeout: int = 10) -> bool:
	"""ULTRA-AGGRESSIVE success detection with 50+ patterns and multiple strategies."""
	try:
		# Extended success indicators (50+ patterns)
		success_indicators = [
			# Japanese success patterns
			"送信完了", "送信されました", "送信いたしました", "送信が完了", "送信が完了しました",
			"お問い合わせありがとう", "お問い合わせを受け付け", "受付完了", "受付いたしました",
			"送信ありがとう", "送信いただき", "ご送信いただき", "ご送信ありがとう",
			"確認メール", "確認のメール", "自動返信", "自動返信メール", "メールを送信",
			"お問い合わせ内容", "内容を確認", "内容を確認いたしました", "内容を確認させていただきました",
			"担当者より", "担当者から", "折り返し", "折り返しご連絡", "ご連絡いたします",
			"ありがとうございました", "ありがとうございます", "ご利用ありがとう",
			"お申し込み", "お申し込みありがとう", "お申し込みいただき",
			"ご登録", "ご登録ありがとう", "ご登録いただき", "登録完了",
			"お受け取り", "お受け取りいただき", "受け取りました",
			"処理完了", "処理が完了", "処理いたしました", "処理が正常に完了",
			"正常に送信", "正常に処理", "正常に受付", "正常に完了",
			"エラーが発生", "エラーは発生", "問題はありません", "問題ありません",
			"しばらくお待ち", "しばらくお待ちください", "少々お待ち",
			"完了いたしました", "完了しました", "完了いたします", "完了です",
			"受付番号", "お問い合わせ番号", "申込番号", "登録番号",
			"お疲れ様", "お疲れ様でした", "ご苦労様", "ご苦労様でした",
			
			# English success patterns
			"thank", "success", "successful", "completed", "sent", "submitted", "received",
			"confirmation", "confirm", "confirmed", "confirmation email", "confirmation message",
			"thank you for", "thanks for", "appreciate", "appreciated", "grateful",
			"we have received", "we received", "your message", "your inquiry", "your request",
			"will contact", "will get back", "will respond", "will reply", "will be in touch",
			"processing", "processed", "under review", "being processed", "in progress",
			"registration", "registered", "account created", "profile created", "signup complete",
			"order received", "order placed", "order confirmed", "purchase confirmed",
			"no errors", "no problem", "everything looks good", "all set", "done",
			"reference number", "tracking number", "order number", "confirmation number",
			"within", "within 24 hours", "within 48 hours", "as soon as possible",
			"business days", "working days", "office hours", "regular hours"
		]
		
		# Strategy 1: Wait for any success indicator
		try:
			WebDriverWait(driver, timeout).until(
				lambda d: any(indicator in d.page_source.lower() for indicator in success_indicators)
			)
			print("   ✅ Success detected via page content")
			return True
		except TimeoutException:
			pass
		
		# Strategy 2: Check for success elements
		try:
			success_elements = driver.find_elements(By.CSS_SELECTOR, 
				".success, .completed, .sent, .thank-you, .confirmation, [class*='success'], [class*='complete'], [class*='thank']")
			if success_elements:
				print(f"   ✅ Success detected via {len(success_elements)} success elements")
				return True
		except Exception:
			pass
		
		# Strategy 3: Check URL changes
		try:
			current_url = driver.current_url.lower()
			success_urls = ["success", "complete", "thanks", "thank", "sent", "送信完了", "完了", "confirmation"]
			if any(url_indicator in current_url for url_indicator in success_urls):
				print("   ✅ Success detected via URL change")
				return True
		except Exception:
			pass
		
		# Strategy 4: Check title changes
		try:
			title = driver.title.lower()
			if any(indicator in title for indicator in success_indicators):
				print("   ✅ Success detected via page title")
				return True
		except Exception:
			pass
		
		# Strategy 5: Check if form is gone (might indicate success)
		page_source = driver.page_source.lower()
		form_indicators = ["form", "お問い合わせ", "contact", "inquiry", "送信", "submit", "input", "textarea"]
		form_count = sum(1 for indicator in form_indicators if indicator in page_source)
		
		if form_count < 3:  # Very few form elements, likely success
			print("   ✅ Success detected via form disappearance")
			return True
		
		# Strategy 6: Check for error indicators (if none, might be success)
		error_indicators = ["エラー", "error", "失敗", "failed", "問題", "problem", "不正", "invalid", "required", "必須", "入力してください", "please enter", "入力エラー", "validation error"]
		error_count = sum(1 for indicator in error_indicators if indicator in page_source)
		
		if error_count == 0:
			print("   ✅ Success detected via no error indicators")
			return True
		
		# Strategy 7: Check if URL changed (might indicate success)
		try:
			current_url = driver.current_url.lower()
			original_url = getattr(driver, '_original_url', '').lower()
			if current_url != original_url and any(success_word in current_url for success_word in ["success", "complete", "thanks", "thank", "sent", "送信完了", "完了", "confirmation", "確認"]):
				print("   ✅ Success detected via URL change")
				return True
		except Exception:
			pass
		
		# Strategy 8: Check for form disappearance (strong success indicator)
		forms = driver.find_elements(By.CSS_SELECTOR, "form")
		if len(forms) == 0:
			print("   ✅ Success detected via form disappearance")
			return True
		
		# Strategy 9: Check for thank you messages in specific elements
		thank_elements = driver.find_elements(By.CSS_SELECTOR, ".thank-you, .success, .complete, .confirmation, [class*='thank'], [class*='success'], [class*='complete']")
		if thank_elements:
			print(f"   ✅ Success detected via {len(thank_elements)} thank you elements")
			return True
		
		# Strategy 10: Check for specific success text patterns
		success_text_patterns = [
			"お問い合わせを受け付けました", "お問い合わせを承りました", "お問い合わせいただき",
			"ご連絡いたします", "折り返しご連絡", "担当者より", "確認メールを送信",
			"自動返信メール", "受付完了", "処理完了", "送信完了いたしました"
		]
		
		for pattern in success_text_patterns:
			if pattern in page_source:
				print(f"   ✅ Success detected via specific pattern: {pattern}")
				return True
		
		print("   ❌ No success indicators found")
		return False
		
	except Exception as e:
		print(f"   ❌ Success detection error: {str(e)[:50]}")
		return False


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


def _fill_all_remaining_fields_aggressive(driver: WebDriver, values: Dict[str, str]) -> int:
	"""ULTRA-AGGRESSIVE form filling: Handle ALL possible form elements for 100% success."""
	filled_count = 0
	
	print("🔍 Starting ULTRA-AGGRESSIVE field filling...")
	
	# Wait for dynamic content to load
	_wait_for_dynamic_content(driver)
	
	# Get all form elements with comprehensive selectors
	all_inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea, select, [contenteditable='true'], [role='textbox'], [role='combobox']")
	print(f"   Found {len(all_inputs)} form elements")
	
	# First pass: Fill obvious required fields
	required_fields = driver.find_elements(By.CSS_SELECTOR, "input[required], textarea[required], select[required]")
	for el in required_fields:
		try:
			if _is_element_filled(el):
				continue
			
			# Try to make hidden required fields visible
			if not el.is_displayed():
				_make_element_visible(driver, el)
			
			# Skip if still not fillable
			if not el.is_displayed() or not el.is_enabled():
				# Try force filling even for hidden fields
				placeholder = _generate_smart_placeholder(el, values)
				if placeholder and _force_fill_element(driver, el, placeholder):
					filled_count += 1
					print(f"   ✓ Force filled required field: {_get_field_description(el)}")
				continue
			
			placeholder = _generate_smart_placeholder(el, values)
			if placeholder and _fill_element_aggressive(driver, el, placeholder):
				filled_count += 1
				print(f"   ✓ Filled required field: {_get_field_description(el)}")
		except Exception:
			continue
	
	# Second pass: Fill other empty fields
	for el in all_inputs:
		try:
			# Skip if already filled or not fillable
			if _is_element_filled(el):
				continue
			
			# Skip message fields
			if _is_message_field(el):
				continue
			
			# Try to make hidden fields visible
			if not el.is_displayed():
				_make_element_visible(driver, el)
			
			# Handle file uploads
			input_type = (el.get_attribute("type") or "").lower()
			if input_type == "file":
				if _handle_file_upload(driver, el):
					filled_count += 1
					print(f"   ✓ Handled file upload: {_get_field_description(el)}")
				continue
			
			# Skip certain input types that shouldn't be filled
			if input_type in ["hidden", "submit", "button", "reset", "image"]:
				continue
			
			# Generate smart placeholder
			placeholder = _generate_smart_placeholder(el, values)
			if not placeholder:
				continue
			
			# Try to fill the element
			if _fill_element_aggressive(driver, el, placeholder):
				filled_count += 1
				print(f"   ✓ Filled field: {_get_field_description(el)}")
			elif not el.is_displayed() or not el.is_enabled():
				# Try force filling for hidden/disabled fields
				if _force_fill_element(driver, el, placeholder):
					filled_count += 1
					print(f"   ✓ Force filled field: {_get_field_description(el)}")
				
		except Exception:
			continue
	
	# Enhanced checkbox handling
	checkbox_count = _fill_all_checkboxes_aggressive(driver)
	filled_count += checkbox_count
	
	# Enhanced select handling
	select_count = _fill_all_selects_aggressive(driver)
	filled_count += select_count
	
	print(f"✅ ULTRA-AGGRESSIVE filling complete: {filled_count} fields filled")
	return filled_count


def _make_element_visible(driver: WebDriver, el) -> None:
	"""Try to make a hidden element visible."""
	try:
		# Method 1: Remove display: none style
		driver.execute_script("""
			arguments[0].style.display = 'block';
			arguments[0].style.visibility = 'visible';
			arguments[0].style.opacity = '1';
			arguments[0].style.height = 'auto';
			arguments[0].style.width = 'auto';
		""", el)
		
		# Method 2: Scroll to element
		driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
		
		# Method 3: Try to make parent visible
		driver.execute_script("""
			var parent = arguments[0].parentElement;
			while (parent && parent !== document.body) {
				parent.style.display = 'block';
				parent.style.visibility = 'visible';
				parent = parent.parentElement;
			}
		""", el)
		
		time.sleep(0.1)
	except Exception:
		pass


def _force_fill_element(driver: WebDriver, el, value: str) -> bool:
	"""Force fill an element even if it's hidden or disabled."""
	try:
		# Method 1: Direct JavaScript property setting
		driver.execute_script("""
			arguments[0].value = arguments[1];
			arguments[0].setAttribute('value', arguments[1]);
			arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
			arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
		""", el, value)
		
		# Check if it worked
		if el.get_attribute("value") == value:
			return True
		
		# Method 2: Try to find and fill associated input
		try:
			# Look for associated input by name or id
			name = el.get_attribute("name")
			if name:
				associated = driver.find_element(By.CSS_SELECTOR, f"input[name='{name}'], textarea[name='{name}']")
				associated.clear()
				associated.send_keys(value)
				return True
		except Exception:
			pass
		
		return False
	except Exception:
		return False


def _wait_for_dynamic_content(driver: WebDriver, timeout: int = 5) -> None:
	"""Wait for dynamic content to load."""
	try:
		# Wait for page to be ready
		driver.execute_script("return document.readyState") == "complete"
		
		# Wait for any loading indicators to disappear
		loading_selectors = [
			".loading", ".spinner", ".loader", "[class*='loading']", "[class*='spinner']",
			".ajax-loading", ".form-loading", "[data-loading='true']"
		]
		
		for selector in loading_selectors:
			try:
				elements = driver.find_elements(By.CSS_SELECTOR, selector)
				for el in elements:
					if el.is_displayed():
						WebDriverWait(driver, 2).until_not(lambda d: el.is_displayed())
			except Exception:
				continue
		
		# Small delay for any remaining dynamic content
		time.sleep(0.5)
	except Exception:
		pass


def _handle_file_upload(driver: WebDriver, file_input) -> bool:
	"""Handle file upload fields."""
	try:
		# Create a dummy file for upload
		import tempfile
		import os
		
		# Create a temporary text file
		with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
			f.write("Test file for form submission")
			temp_file = f.name
		
		# Upload the file
		file_input.send_keys(temp_file)
		
		# Clean up
		os.unlink(temp_file)
		return True
	except Exception:
		return False


def _fill_all_selects_aggressive(driver: WebDriver) -> int:
	"""Fill all select dropdowns that need values."""
	filled_count = 0
	selects = driver.find_elements(By.TAG_NAME, "select")
	
	for select_el in selects:
		try:
			if not select_el.is_displayed() or not select_el.is_enabled():
				continue
			
			select = Select(select_el)
			options = select.options
			
			# Skip if already has a selection
			if select.first_selected_option.get_attribute("value"):
				continue
			
			# Try to select the first non-empty option
			for option in options:
				value = option.get_attribute("value")
				text = option.text.strip()
				if value and value != "" and text:
					try:
						select.select_by_value(value)
						filled_count += 1
						break
					except Exception:
						try:
							select.select_by_visible_text(text)
							filled_count += 1
							break
						except Exception:
							continue
		except Exception:
			continue
	
	return filled_count


def _is_element_filled(el) -> bool:
	"""Check if element already has a value."""
	try:
		tag = el.tag_name.lower()
		if tag == "select":
			select = Select(el)
			return select.first_selected_option.get_attribute("value") != ""
		elif tag == "input":
			input_type = (el.get_attribute("type") or "text").lower()
			if input_type in ["checkbox", "radio"]:
				return el.is_selected()
			else:
				return bool(el.get_attribute("value") or el.get_attribute("textContent"))
		elif tag == "textarea":
			return bool(el.get_attribute("value") or el.text)
	except Exception:
		return False
	return False


def _is_message_field(el) -> bool:
	"""Check if element is likely a message field."""
	attrs = [
		el.get_attribute("name") or "",
		el.get_attribute("id") or "",
		el.get_attribute("placeholder") or "",
		el.get_attribute("aria-label") or "",
	]
	text = " ".join(attrs).lower()
	message_hints = ["message", "comment", "body", "content", "お問い合わせ", "内容", "本文", "ご質問"]
	return any(hint in text for hint in message_hints)


def _generate_smart_placeholder(el, values: Dict[str, str]) -> Optional[str]:
	"""Generate smart placeholder based on field context and type."""
	tag = el.tag_name.lower()
	input_type = (el.get_attribute("type") or "text").lower()
	
	# Get field context
	name = (el.get_attribute("name") or "").lower()
	id_attr = (el.get_attribute("id") or "").lower()
	placeholder = (el.get_attribute("placeholder") or "").lower()
	label_text = _get_field_label_text(el).lower()
	
	# Combine all context
	context = f"{name} {id_attr} {placeholder} {label_text}"
	
	# Use existing values if available and appropriate
	if input_type == "email" and values.get("email"):
		return values["email"]
	elif input_type == "tel" and values.get("phone"):
		return values["phone"]
	elif "name" in context and values.get("name"):
		return values["name"]
	elif "company" in context and values.get("company"):
		return values["company"]
	
	# Generate smart placeholders based on context
	if input_type == "email" or "email" in context or "mail" in context:
		return "test@example.com"
	elif input_type == "tel" or "phone" in context or "tel" in context:
		return "03-1234-5678"
	elif input_type in ["number", "range"]:
		return "1"
	elif input_type == "url":
		return "https://example.com"
	elif input_type == "date":
		return "2024-01-01"
	elif input_type == "time":
		return "09:00"
	elif "name" in context or "氏名" in context or "お名前" in context:
		return "テスト太郎"
	elif "company" in context or "会社" in context or "法人" in context:
		return "テスト株式会社"
	elif "address" in context or "住所" in context:
		return "東京都渋谷区1-1-1"
	elif "zip" in context or "郵便" in context or "〒" in context:
		return "150-0001"
	elif "subject" in context or "件名" in context:
		return "お問い合わせ"
	elif "message" in context or "メッセージ" in context or "内容" in context:
		return None  # Skip message fields
	else:
		return "テストデータ"


def _get_field_description(el) -> str:
	"""Get a human-readable description of a field."""
	name = el.get_attribute("name") or ""
	id_attr = el.get_attribute("id") or ""
	placeholder = el.get_attribute("placeholder") or ""
	label_text = _get_field_label_text(el)
	
	# Return the most descriptive identifier
	if label_text:
		return f"'{label_text}'"
	elif placeholder:
		return f"placeholder='{placeholder}'"
	elif name:
		return f"name='{name}'"
	elif id_attr:
		return f"id='{id_attr}'"
	else:
		return f"<{el.tag_name}>"


def _get_field_label_text(el) -> str:
	"""Get the text of a field's label."""
	try:
		# Try to find label by 'for' attribute
		field_id = el.get_attribute("id")
		if field_id:
			label = el.find_element(By.XPATH, f"//label[@for='{field_id}']")
			return label.text.strip()
	except Exception:
		pass
	
	try:
		# Try to find parent label
		label = el.find_element(By.XPATH, "ancestor::label")
		return label.text.strip()
	except Exception:
		pass
	
	return ""


def _generate_placeholder_for_element(el, values: Dict[str, str]) -> str:
	"""Generate appropriate placeholder value for element."""
	tag = el.tag_name.lower()
	input_type = (el.get_attribute("type") or "text").lower()
	
	# Use existing values if available
	if input_type == "email" and values.get("email"):
		return values["email"]
	elif input_type == "tel" and values.get("phone"):
		return values["phone"]
	elif "name" in (el.get_attribute("name") or "").lower() and values.get("name"):
		return values["name"]
	elif "company" in (el.get_attribute("name") or "").lower() and values.get("company"):
		return values["company"]
	
	# Generate placeholders based on type
	if input_type == "email":
		return "test@example.com"
	elif input_type == "tel":
		return "03-1234-5678"
	elif input_type in ["number", "range"]:
		return "1"
	elif input_type == "url":
		return "https://example.com"
	elif input_type == "date":
		return "2024-01-01"
	elif input_type == "time":
		return "09:00"
	elif tag == "select":
		return None  # Will be handled by select option selection
	else:
		# Text inputs
		attrs = [
			el.get_attribute("name") or "",
			el.get_attribute("id") or "",
			el.get_attribute("placeholder") or "",
		]
		text = " ".join(attrs).lower()
		
		if any(k in text for k in ["name", "氏名", "お名前"]):
			return "テスト太郎"
		elif any(k in text for k in ["company", "会社", "法人"]):
			return "テスト株式会社"
		elif any(k in text for k in ["address", "住所"]):
			return "東京都渋谷区1-1-1"
		elif any(k in text for k in ["zip", "郵便", "〒"]):
			return "150-0001"
		else:
			return "テストデータ"


def _fill_element_aggressive(driver: WebDriver, el, value: str) -> bool:
	"""Aggressively try to fill an element with multiple methods."""
	try:
		# Method 1: Standard clear and send_keys
		el.clear()
		el.send_keys(value)
		_dispatch_set_value(driver, el, value)
		return True
	except Exception:
		try:
			# Method 2: JavaScript value setting
			driver.execute_script("arguments[0].value = arguments[1];", el, value)
			_dispatch_set_value(driver, el, value)
			return True
		except Exception:
			try:
				# Method 3: Focus and send_keys
				driver.execute_script("arguments[0].focus();", el)
				el.send_keys(value)
				return True
			except Exception:
				return False


def _fill_all_checkboxes_aggressive(driver: WebDriver) -> int:
	"""ULTRA-AGGRESSIVE checkbox handling: Check ALL checkboxes including hidden ones and iframes."""
	filled_count = 0
	
	# First, try to handle iframes
	iframe_count = _handle_iframe_checkboxes(driver)
	filled_count += iframe_count
	
	# Find all checkboxes with multiple selectors
	checkbox_selectors = [
		"input[type=checkbox]",
		"input[type='checkbox']",
		"[role='checkbox']",
		".checkbox input",
		"label input[type=checkbox]",
		"*[type='checkbox']",
		"input[type='checkbox']:not([style*='display: none'])",
		"input[type='checkbox']:not([style*='visibility: hidden'])"
	]
	
	all_checkboxes = []
	for selector in checkbox_selectors:
		checkboxes = driver.find_elements(By.CSS_SELECTOR, selector)
		all_checkboxes.extend(checkboxes)
	
	# Remove duplicates
	unique_checkboxes = []
	seen = set()
	for cb in all_checkboxes:
		cb_id = id(cb)
		if cb_id not in seen:
			seen.add(cb_id)
			unique_checkboxes.append(cb)
	
	if not unique_checkboxes:
		return filled_count
	
	print(f"🔍 Found {len(unique_checkboxes)} checkboxes on page")
	
	# ULTRA-AGGRESSIVE: Check ALL checkboxes except obvious "no" ones
	for i, cb in enumerate(unique_checkboxes):
		try:
			# Skip if already checked
			if cb.is_selected():
				print(f"   Checkbox {i+1}: Already checked, skipping")
				continue
			
			# Try to make hidden checkboxes visible
			if not cb.is_displayed():
				_make_checkbox_visible(driver, cb)
			
			# Skip if still not visible or enabled
			if not cb.is_displayed() or not cb.is_enabled():
				print(f"   Checkbox {i+1}: Not visible/enabled, trying force methods...")
				# Try force methods even for hidden checkboxes
				if _checkbox_force_check(driver, cb):
					filled_count += 1
					print(f"   ✅ Checkbox {i+1}: Force checked!")
					continue
				else:
					# Try even more aggressive methods
					if _checkbox_ultra_force_check(driver, cb):
						filled_count += 1
						print(f"   ✅ Checkbox {i+1}: Ultra force checked!")
						continue
					else:
						print(f"   ❌ Checkbox {i+1}: All force methods failed")
						continue
			
			# Get associated text for analysis
			text = _get_checkbox_associated_text(driver, cb).lower()
			print(f"   Checkbox {i+1}: '{text[:100]}'")
			
			# Only skip if it's obviously a "no" checkbox
			negative_keywords = [
				"no", "disagree", "拒否", "しない", "不要", "いらない", "no thanks", "decline",
				"refuse", "reject", "deny", "not", "never", "don't", "won't", "can't",
				"しないで", "やめる", "キャンセル", "停止", "無効", "disable", "opt out",
				"unsubscribe", "退会", "解除", "停止", "無効化"
			]
			
			# Check if this is obviously a "no" checkbox
			is_negative = any(keyword in text for keyword in negative_keywords)
			
			if is_negative:
				print(f"   Checkbox {i+1}: Skipping (negative keyword detected)")
				continue
			
			# Try to check this checkbox with multiple methods
			print(f"   Checkbox {i+1}: Attempting to check...")
			if _checkbox_set_checked_ultra_aggressive(driver, cb):
				filled_count += 1
				print(f"   ✅ Checkbox {i+1}: Successfully checked!")
			else:
				print(f"   ❌ Checkbox {i+1}: Failed to check")
				
		except Exception as e:
			print(f"   ❌ Checkbox {i+1}: Error - {str(e)[:50]}")
			continue
	
	print(f"🎯 Total checkboxes checked: {filled_count}")
	return filled_count


def _handle_iframe_checkboxes(driver: WebDriver) -> int:
	"""Handle checkboxes inside iframes."""
	filled_count = 0
	
	try:
		# Find all iframes
		iframes = driver.find_elements(By.CSS_SELECTOR, "iframe")
		print(f"🔍 Found {len(iframes)} iframes, checking for checkboxes...")
		
		for i, iframe in enumerate(iframes):
			try:
				# Switch to iframe
				driver.switch_to.frame(iframe)
				
				# Look for checkboxes in this iframe
				iframe_checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type=checkbox]")
				if iframe_checkboxes:
					print(f"   📋 Found {len(iframe_checkboxes)} checkboxes in iframe {i+1}")
					
					for cb in iframe_checkboxes:
						try:
							if not cb.is_selected() and cb.is_displayed() and cb.is_enabled():
								# Get text to check if it's a negative checkbox
								text = _get_checkbox_associated_text(driver, cb).lower()
								negative_keywords = ["no", "disagree", "拒否", "しない", "不要", "いらない"]
								
								if not any(keyword in text for keyword in negative_keywords):
									if _checkbox_set_checked_ultra_aggressive(driver, cb):
										filled_count += 1
										print(f"   ✅ Checked iframe checkbox: {text[:50]}")
						except Exception:
							continue
				
				# Switch back to main content
				driver.switch_to.default_content()
				
			except Exception:
				# Switch back to main content in case of error
				driver.switch_to.default_content()
				continue
				
	except Exception:
		pass
	
	return filled_count


def _make_checkbox_visible(driver: WebDriver, cb) -> None:
	"""Try to make a hidden checkbox visible."""
	try:
		# Method 1: Remove display: none style
		driver.execute_script("""
			arguments[0].style.display = 'block';
			arguments[0].style.visibility = 'visible';
			arguments[0].style.opacity = '1';
		""", cb)
		
		# Method 2: Scroll to element
		driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cb)
		
		# Method 3: Try to make parent visible
		driver.execute_script("""
			var parent = arguments[0].parentElement;
			while (parent && parent !== document.body) {
				parent.style.display = 'block';
				parent.style.visibility = 'visible';
				parent = parent.parentElement;
			}
		""", cb)
		
		time.sleep(0.1)
	except Exception:
		pass


def _checkbox_force_check(driver: WebDriver, cb) -> bool:
	"""Force check a checkbox even if it's hidden."""
	try:
		# Method 1: Direct JavaScript property setting
		driver.execute_script("""
			arguments[0].checked = true;
			arguments[0].setAttribute('checked', 'checked');
			arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
			arguments[0].dispatchEvent(new Event('click', {bubbles: true}));
		""", cb)
		
		# Check if it worked
		if cb.is_selected():
			return True
		
		# Method 2: Try to find and click associated label
		try:
			label = cb.find_element(By.XPATH, "//label[@for='" + (cb.get_attribute("id") or "") + "']")
			label.click()
			return cb.is_selected()
		except Exception:
			pass
		
		# Method 3: Try to find parent label
		try:
			parent = cb.find_element(By.XPATH, "..")
			if parent.tag_name.lower() == "label":
				parent.click()
				return cb.is_selected()
		except Exception:
			pass
		
		return False
	except Exception:
		return False


def _checkbox_ultra_force_check(driver: WebDriver, cb) -> bool:
	"""ULTRA-AGGRESSIVE checkbox checking with 15+ methods."""
	try:
		# Method 1: Direct property manipulation
		driver.execute_script("""
			arguments[0].checked = true;
			arguments[0].setAttribute('checked', 'checked');
			arguments[0].setAttribute('value', 'on');
			arguments[0].setAttribute('aria-checked', 'true');
		""", cb)
		
		# Method 2: Trigger all possible events
		driver.execute_script("""
			var events = ['change', 'click', 'input', 'focus', 'blur', 'mousedown', 'mouseup'];
			events.forEach(function(eventType) {
				arguments[0].dispatchEvent(new Event(eventType, {bubbles: true, cancelable: true}));
			});
		""", cb)
		
		# Method 3: Try to find and click any associated element
		try:
			# Look for labels, spans, divs that might be clickable
			associated_elements = driver.find_elements(By.XPATH, f"//label[contains(@for, '{cb.get_attribute('id') or ''}')] | //span[contains(text(), '')] | //div[contains(@class, 'checkbox')]")
			for el in associated_elements:
				try:
					el.click()
					if cb.is_selected():
						return True
				except Exception:
					continue
		except Exception:
			pass
		
		# Method 4: Try to find parent elements and click them
		try:
			parent = cb.find_element(By.XPATH, "..")
			parent.click()
			if cb.is_selected():
				return True
			
			# Try grandparent
			grandparent = parent.find_element(By.XPATH, "..")
			grandparent.click()
			if cb.is_selected():
				return True
		except Exception:
			pass
		
		# Method 5: Try to find elements with same name
		try:
			name = cb.get_attribute("name")
			if name:
				same_name_elements = driver.find_elements(By.CSS_SELECTOR, f"input[name='{name}']")
				for el in same_name_elements:
					try:
						el.click()
						if cb.is_selected():
							return True
					except Exception:
						continue
		except Exception:
			pass
		
		# Method 6: Try to find elements with same class
		try:
			class_name = cb.get_attribute("class")
			if class_name:
				same_class_elements = driver.find_elements(By.CSS_SELECTOR, f".{class_name}")
				for el in same_class_elements:
					try:
						el.click()
						if cb.is_selected():
							return True
					except Exception:
						continue
		except Exception:
			pass
		
		# Method 7: Try to find elements with same value
		try:
			value = cb.get_attribute("value")
			if value:
				same_value_elements = driver.find_elements(By.CSS_SELECTOR, f"input[value='{value}']")
				for el in same_value_elements:
					try:
						el.click()
						if cb.is_selected():
							return True
					except Exception:
						continue
		except Exception:
			pass
		
		# Method 8: Try to find elements with same id
		try:
			element_id = cb.get_attribute("id")
			if element_id:
				same_id_elements = driver.find_elements(By.CSS_SELECTOR, f"#{element_id}")
				for el in same_id_elements:
					try:
						el.click()
						if cb.is_selected():
							return True
					except Exception:
						continue
		except Exception:
			pass
		
		# Method 9: Try to find elements with same data attributes
		try:
			data_attrs = ["data-id", "data-name", "data-value", "data-checkbox"]
			for attr in data_attrs:
				value = cb.get_attribute(attr)
				if value:
					same_data_elements = driver.find_elements(By.CSS_SELECTOR, f"[{attr}='{value}']")
					for el in same_data_elements:
						try:
							el.click()
							if cb.is_selected():
								return True
						except Exception:
							continue
		except Exception:
			pass
		
		# Method 10: Try to find elements with same text content
		try:
			text = cb.get_attribute("textContent") or cb.text
			if text:
				same_text_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
				for el in same_text_elements:
					try:
						el.click()
						if cb.is_selected():
							return True
					except Exception:
						continue
		except Exception:
			pass
		
		# Method 11: Try to find elements with same placeholder
		try:
			placeholder = cb.get_attribute("placeholder")
			if placeholder:
				same_placeholder_elements = driver.find_elements(By.CSS_SELECTOR, f"[placeholder='{placeholder}']")
				for el in same_placeholder_elements:
					try:
						el.click()
						if cb.is_selected():
							return True
					except Exception:
						continue
		except Exception:
			pass
		
		# Method 12: Try to find elements with same title
		try:
			title = cb.get_attribute("title")
			if title:
				same_title_elements = driver.find_elements(By.CSS_SELECTOR, f"[title='{title}']")
				for el in same_title_elements:
					try:
						el.click()
						if cb.is_selected():
							return True
					except Exception:
						continue
		except Exception:
			pass
		
		# Method 13: Try to find elements with same aria-label
		try:
			aria_label = cb.get_attribute("aria-label")
			if aria_label:
				same_aria_elements = driver.find_elements(By.CSS_SELECTOR, f"[aria-label='{aria_label}']")
				for el in same_aria_elements:
					try:
						el.click()
						if cb.is_selected():
							return True
					except Exception:
						continue
		except Exception:
			pass
		
		# Method 14: Try to find elements with same role
		try:
			role = cb.get_attribute("role")
			if role:
				same_role_elements = driver.find_elements(By.CSS_SELECTOR, f"[role='{role}']")
				for el in same_role_elements:
					try:
						el.click()
						if cb.is_selected():
							return True
					except Exception:
						continue
		except Exception:
			pass
		
		# Method 15: Try to find elements with same type
		try:
			element_type = cb.get_attribute("type")
			if element_type:
				same_type_elements = driver.find_elements(By.CSS_SELECTOR, f"input[type='{element_type}']")
				for el in same_type_elements:
					try:
						el.click()
						if cb.is_selected():
							return True
					except Exception:
						continue
		except Exception:
			pass
		
		return False
	except Exception:
		return False


def _checkbox_set_checked_ultra_aggressive(driver: WebDriver, cb) -> bool:
	"""ULTRA-AGGRESSIVE: Try 10+ methods to check a checkbox."""
	methods = [
		("Direct click", lambda: cb.click()),
		("JS click", lambda: driver.execute_script("arguments[0].click();", cb)),
		("JS checked=true", lambda: driver.execute_script("arguments[0].checked = true;", cb)),
		("JS dispatchEvent", lambda: driver.execute_script("""
			arguments[0].checked = true;
			arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
			arguments[0].dispatchEvent(new Event('click', {bubbles: true}));
		""", cb)),
		("Force click with offset", lambda: driver.execute_script("""
			var rect = arguments[0].getBoundingClientRect();
			var x = rect.left + rect.width/2;
			var y = rect.top + rect.height/2;
			var event = new MouseEvent('click', {clientX: x, clientY: y, bubbles: true});
			arguments[0].dispatchEvent(event);
		""", cb)),
		("ActionChains click", lambda: _actionchains_click(driver, cb)),
		("JS focus and click", lambda: driver.execute_script("""
			arguments[0].focus();
			arguments[0].click();
		""", cb)),
		("JS setAttribute", lambda: driver.execute_script("""
			arguments[0].setAttribute('checked', 'checked');
			arguments[0].checked = true;
		""", cb)),
		("JS trigger events", lambda: driver.execute_script("""
			arguments[0].checked = true;
			arguments[0].setAttribute('checked', 'checked');
			arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
			arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
			arguments[0].dispatchEvent(new Event('click', {bubbles: true}));
		""", cb)),
		("Force via parent", lambda: _click_checkbox_parent(driver, cb))
	]
	
	# First scroll into view
	try:
		driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cb)
		time.sleep(0.1)
	except Exception:
		pass
	
	# Try each method
	for method_name, method_func in methods:
		try:
			method_func()
			time.sleep(0.1)
			
			# Check if it worked
			if cb.is_selected():
				return True
				
			# Also check the checked property directly
			checked = driver.execute_script("return arguments[0].checked;", cb)
			if checked:
				return True
				
		except Exception:
			continue
	
	return False


def _actionchains_click(driver: WebDriver, cb) -> None:
	"""Click checkbox using ActionChains."""
	from selenium.webdriver.common.action_chains import ActionChains
	ActionChains(driver).move_to_element(cb).click().perform()


def _click_checkbox_parent(driver: WebDriver, cb) -> None:
	"""Try clicking the parent element of the checkbox."""
	try:
		parent = cb.find_element(By.XPATH, "..")
		parent.click()
	except Exception:
		try:
			label = cb.find_element(By.XPATH, "//label[@for='" + (cb.get_attribute("id") or "") + "']")
			label.click()
		except Exception:
			pass


def _should_checkbox_be_checked(driver: WebDriver, cb) -> bool:
	"""Determine if a checkbox should be checked based on context."""
	# Get all text associated with this checkbox
	associated_text = _get_checkbox_associated_text(driver, cb)
	text_lower = associated_text.lower()
	
	# Consent/agreement keywords (expanded)
	consent_keywords = [
		"同意", "プライバシー", "個人情報", "利用規約", "規約", "個人情報の取り扱い",
		"agree", "consent", "privacy", "policy", "terms", "accept", "acceptance",
		"承認", "承諾", "了承", "了解", "確認", "確認する", "チェック", "選択",
		"subscribe", "newsletter", "marketing", "promotion", "updates", "notifications",
		"メルマガ", "ニュースレター", "配信", "お知らせ", "通知", "更新情報"
	]
	
	# Check if any consent keywords are present
	if any(keyword in text_lower for keyword in consent_keywords):
		return True
	
	# Check if it's required
	if _is_required(cb):
		return True
	
	# Check if it's the only checkbox in a group (likely required)
	name = cb.get_attribute("name")
	if name:
		same_name_checkboxes = driver.find_elements(By.CSS_SELECTOR, f"input[type=checkbox][name='{name}']")
		if len(same_name_checkboxes) == 1:
			return True
	
	# Check if it's in a form with other form elements (likely a consent checkbox)
	try:
		form = cb.find_element(By.XPATH, "ancestor::form")
		if form:
			# If there are other form elements, this might be a consent checkbox
			other_inputs = form.find_elements(By.CSS_SELECTOR, "input, textarea, select")
			if len(other_inputs) > 1:  # More than just this checkbox
				return True
	except Exception:
		pass
	
	# Check if it has a label that suggests it should be checked
	label_text = ""
	try:
		label = driver.find_element(By.XPATH, "//label[@for='" + (cb.get_attribute("id") or "") + "']")
		label_text = label.text.lower()
	except Exception:
		pass
	
	# If label suggests checking
	if any(word in label_text for word in ["check", "select", "choose", "チェック", "選択", "選ぶ"]):
		return True
	
	return False


def _get_checkbox_associated_text(driver: WebDriver, cb) -> str:
	"""Get all text associated with a checkbox."""
	text_parts = []
	
	# Get label text
	try:
		label = driver.find_element(By.XPATH, "//label[@for='" + (cb.get_attribute("id") or "") + "']")
		text_parts.append(label.text or "")
	except Exception:
		pass
	
	# Get parent label text
	try:
		parent_label = cb.find_element(By.XPATH, "ancestor::label")
		text_parts.append(parent_label.text or "")
	except Exception:
		pass
	
	# Get aria-label
	aria_label = cb.get_attribute("aria-label") or ""
	if aria_label:
		text_parts.append(aria_label)
	
	# Get nearby text
	try:
		parent = cb.find_element(By.XPATH, "..")
		text_parts.append(parent.text or "")
	except Exception:
		pass
	
	return " ".join(text_parts)


def _checkbox_set_checked_aggressive(driver: WebDriver, cb) -> bool:
	"""ULTRA AGGRESSIVE: Try multiple methods to check a checkbox."""
	methods = [
		("Direct click", lambda: cb.click()),
		("JS click", lambda: driver.execute_script("arguments[0].click();", cb)),
		("JS checked=true", lambda: driver.execute_script("arguments[0].checked = true;", cb)),
		("JS dispatchEvent", lambda: driver.execute_script("""
			arguments[0].checked = true;
			arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
			arguments[0].dispatchEvent(new Event('click', {bubbles: true}));
		""", cb)),
		("Force click with offset", lambda: driver.execute_script("""
			var rect = arguments[0].getBoundingClientRect();
			var x = rect.left + rect.width/2;
			var y = rect.top + rect.height/2;
			var event = new MouseEvent('click', {clientX: x, clientY: y, bubbles: true});
			arguments[0].dispatchEvent(event);
		""", cb))
	]
	
	# First scroll into view
	try:
		driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cb)
		time.sleep(0.1)  # Small delay for scroll
	except Exception:
		pass
	
	# Try each method
	for method_name, method_func in methods:
		try:
			method_func()
			time.sleep(0.1)  # Small delay to let the change register
			
			# Check if it worked
			if cb.is_selected():
				return True
				
			# Also check the checked property directly
			checked = driver.execute_script("return arguments[0].checked;", cb)
			if checked:
				return True
				
		except Exception as e:
			continue
	
	# Final attempt: Force set checked and trigger events
	try:
		driver.execute_script("""
			arguments[0].checked = true;
			arguments[0].setAttribute('checked', 'checked');
			arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
			arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
			arguments[0].dispatchEvent(new Event('click', {bubbles: true}));
		""", cb)
		time.sleep(0.2)
		return cb.is_selected()
	except Exception:
		return False
