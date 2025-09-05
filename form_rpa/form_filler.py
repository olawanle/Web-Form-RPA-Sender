from __future__ import annotations

import re
import time
from typing import Dict, Optional, Tuple, List

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException


FIELD_HINTS = {
	"name": ["name", "your-name", "fullname", "full-name", "contact", "お名前", "氏名"],
	"company": ["company", "organization", "corp", "company-name", "会社", "御社", "貴社"],
	"email": ["email", "mail", "e-mail", "your-email", "メール"],
	"phone": ["phone", "tel", "telephone", "携帯", "電話"],
	"subject": ["subject", "件名", "題名"],
	"message": ["message", "inquiry", "contact", "body", "comment", "お問い合わせ", "内容", "本文"],
}

SUBMIT_HINTS = [
	"submit", "send", "送信", "確認", "confirm", "お問い合わせ送信"
]


def _find_by_label_association(driver: WebDriver, keywords: List[str]):
	labels = driver.find_elements(By.TAG_NAME, "label")
	for label in labels:
		text = (label.text or "").lower()
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


def fill_fields(driver: WebDriver, values: Dict[str, str]) -> Dict[str, bool]:
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
	return result


def _elements_with_text(driver: WebDriver, selector: str, hints: List[str]):
	matches = []
	for el in driver.find_elements(By.CSS_SELECTOR, selector):
		text = ((el.text or "") + " " + (el.get_attribute("value") or "")).strip().lower()
		if any(h in text for h in hints):
			matches.append(el)
	return matches


def _submit_enclosing_form(driver: WebDriver) -> bool:
	# If there is exactly one form, submit it
	forms = driver.find_elements(By.TAG_NAME, "form")
	if len(forms) == 1:
		try:
			driver.execute_script("arguments[0].submit();", forms[0])
			return True
		except Exception:
			pass
	# Otherwise, find a form that contains typical fields
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
	# Try common submit-like elements
	selector_sets = [
		("button[type=submit], input[type=submit]", SUBMIT_HINTS),
		("button, input[type=button]", SUBMIT_HINTS),
		("[role=button]", SUBMIT_HINTS),
		("a", SUBMIT_HINTS),
	]
	for selector, hints in selector_sets:
		for el in _elements_with_text(driver, selector, [h.lower() for h in hints]):
			try:
				el.click()
				return True
			except Exception:
				continue
	# Fallback: submit the enclosing form
	if _submit_enclosing_form(driver):
		return True
	return False


def wait_post_submit(driver: WebDriver, timeout: int = 10) -> None:
	try:
		WebDriverWait(driver, timeout).until(
			lambda d: "thank" in d.page_source.lower() or "成功" in d.page_source or "受け付け" in d.page_source or "送信" in d.page_source
		)
	except TimeoutException:
		pass
