from __future__ import annotations

import os
import random
import time
from datetime import datetime
from typing import Callable, Dict, Optional

from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.common.by import By

from .ai_assist import suggest_selectors, generate_values
from .browser import create_chrome_driver
from .captcha import is_captcha_present
from .form_filler import fill_fields, click_submit, wait_post_submit, multi_step_submit, detect_required_errors, collect_required_fields
from .lead_loader import load_leads, dedupe_against_log
from .logging_utils import append_log
from .quota import remaining_quota
from .template_engine import render_template, build_salutation


ProgressCallback = Callable[[Dict[str, str]], None]


def _sanitize_filename(text: str) -> str:
	bad = "<>:\\\"/|?*\n\r\t"
	out = "".join(ch if ch not in bad else "_" for ch in (text or "")).strip()
	return out[:80] or "lead"


def _wait_dom_ready(driver, timeout: int = 15):
	start = time.time()
	while time.time() - start < timeout:
		try:
			state = driver.execute_script("return document.readyState")
			if state in ("interactive", "complete"):
				return True
		except WebDriverException:
			return False
		time.sleep(0.2)
	return False


def _apply_ai_selectors(driver, selectors: Dict[str, object], values: Dict[str, str]) -> bool:
	success = False
	def _find(css: str):
		try:
			return driver.find_element(By.CSS_SELECTOR, css)
		except NoSuchElementException:
			return None
	# Fill known fields
	for key in ["name", "company", "email", "phone", "subject", "message"]:
		css = selectors.get(key)
		if isinstance(css, str) and css.strip():
			el = _find(css)
			if el is not None and values.get(key):
				try:
					el.clear()
					el.send_keys(values[key])
					success = True
				except Exception:
					pass
	# Consents
	consents = selectors.get("consents")
	if isinstance(consents, list):
		for css in consents:
			el = _find(css)
			if el is not None:
				try:
					if not el.is_selected():
						el.click()
				except Exception:
					pass
	# Submit
	submit_css = selectors.get("submit")
	if isinstance(submit_css, str) and submit_css.strip():
		btn = _find(submit_css)
		if btn is not None:
			try:
				btn.click()
				success = True
			except Exception:
				pass
	return success


def process_leads(
	input_path: str,
	template_path: str,
	log_path: str = "send_log.csv",
	max_per_day: int = 500,
	start_time: Optional[str] = None,
	headless: bool = True,
	skip_on_captcha: bool = True,
	sleep_min: float = 1.0,
	sleep_max: float = 3.0,
	preview: bool = False,
	screenshot_dir: Optional[str] = None,
	auto_consent: bool = True,
	use_multistep_submit: bool = True,
	ai_assist_mode: str = "always",  # default always-on
	openrouter_api_key: Optional[str] = None,
	ai_fill_required: bool = True,
	on_progress: Optional[ProgressCallback] = None,
) -> None:
	"""Run the end-to-end lead processing workflow."""
	def _emit(event: Dict[str, str]) -> None:
		if on_progress:
			on_progress(event)

	def _wait_until(start_time_str: Optional[str]) -> None:
		if not start_time_str:
			return
		now = datetime.now()
		try:
			if len(start_time_str) == 5 and ":" in start_time_str:
				target = datetime.strptime(start_time_str, "%H:%M").replace(
					year=now.year, month=now.month, day=now.day
				)
				if target <= now:
					target = target.replace(day=now.day + 1)
			else:
				target = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
			delta = (target - now).total_seconds()
			if delta > 0:
				time.sleep(delta)
		except Exception:
			return

	if screenshot_dir:
		os.makedirs(screenshot_dir, exist_ok=True)

	_wait_until(start_time)
	leads = load_leads(input_path)
	leads, _ = dedupe_against_log(leads, log_path)
	remaining = remaining_quota(max_per_day, log_path)
	if remaining <= 0:
		_emit({"event": "quota_reached"})
		return

	driver = create_chrome_driver(headless=headless)
	count = 0
	try:
		for idx, row in leads.iterrows():
			if count >= remaining:
				break
			inquiry_url = row["inquiry_url"]
			company_name = row.get("company_name", "")
			contact_name = row.get("contact_name", "")
			name_value = contact_name or company_name
			context = {
				"salutation": build_salutation(contact_name or company_name, honorific="Dear"),
				"company_name": company_name,
				"contact_name": contact_name,
			}
			lead_prefix = f"{count+1:03d}_" + _sanitize_filename(company_name)
			try:
				try:
					driver.get(inquiry_url)
				except WebDriverException:
					driver.quit()
					driver = create_chrome_driver(headless=headless)
					driver.get(inquiry_url)

				_wait_dom_ready(driver, timeout=15)

				shot_loaded = ""
				if screenshot_dir:
					shot_loaded = os.path.join(screenshot_dir, f"{lead_prefix}_loaded.png")
					driver.save_screenshot(shot_loaded)
				_emit({"event": "loaded", "company_name": company_name, "url": inquiry_url, "screenshot": shot_loaded})

				if skip_on_captcha and is_captcha_present(driver):
					append_log(log_path, {
						"company_name": company_name,
						"inquiry_url": inquiry_url,
						"status": "captcha_skipped",
						"detail": "CAPTCHA detected before fill"
					})
					_emit({"event": "captcha_skipped", "company_name": company_name, "url": inquiry_url})
					continue

				message = render_template(template_path, context)
				values = {
					"name": name_value,
					"company": company_name,
					"email": row.get("email", ""),
					"phone": row.get("phone", ""),
					"subject": row.get("subject", ""),
					"message": message,
				}
				fill_fields(driver, values, auto_consent=auto_consent)

				if ai_assist_mode in ("always",):
					html = driver.page_source
					selectors = suggest_selectors(html, api_key=openrouter_api_key)
					_apply_ai_selectors(driver, selectors, values)

				if preview:
					append_log(log_path, {"company_name": company_name, "inquiry_url": inquiry_url, "status": "preview", "detail": "No submit (preview mode)"})
					count += 1
					time.sleep(random.uniform(sleep_min, sleep_max))
					continue

				clicked = multi_step_submit(driver) if use_multistep_submit else click_submit(driver)
				if not clicked and ai_assist_mode in ("failure_only",):
					html = driver.page_source
					selectors = suggest_selectors(html, api_key=openrouter_api_key)
					if _apply_ai_selectors(driver, selectors, values):
						clicked = True

				# If required errors, try AI to generate values and resubmit once
				if (not preview) and ai_fill_required and detect_required_errors(driver):
					required = collect_required_fields(driver)
					gen = generate_values(required, {"company_name": company_name, "contact_name": contact_name}, api_key=openrouter_api_key)
					# Fill generated values by name/id
					for item in required:
						key = item.get("key")
						val = gen.get(key, "")
						if not val:
							continue
						# Try select by name or id
						name = item.get("name") or ""
						fid = item.get("id") or ""
						el = None
						if name:
							try:
								el = driver.find_element(By.NAME, name)
							except Exception:
								pass
						if el is None and fid:
							try:
								el = driver.find_element(By.ID, fid)
							except Exception:
								pass
						if el is not None:
							try:
								el.clear()
								el.send_keys(val)
							except Exception:
								pass
					# Retry submit
					clicked = clicked or (multi_step_submit(driver) if use_multistep_submit else click_submit(driver))

				if not clicked:
					append_log(log_path, {"company_name": company_name, "inquiry_url": inquiry_url, "status": "failed", "detail": "Submit button not found"})
					_emit({"event": "failed", "company_name": company_name, "url": inquiry_url, "reason": "submit_not_found"})
					continue

				wait_post_submit(driver)
				shot_after = ""
				if screenshot_dir:
					shot_after = os.path.join(screenshot_dir, f"{lead_prefix}_after_submit.png")
					driver.save_screenshot(shot_after)
				_emit({"event": "submitted_wait", "company_name": company_name, "url": inquiry_url, "screenshot": shot_after})

				if skip_on_captcha and is_captcha_present(driver):
					append_log(log_path, {"company_name": company_name, "inquiry_url": inquiry_url, "status": "captcha_skipped", "detail": "CAPTCHA after submit"})
					_emit({"event": "captcha_skipped", "company_name": company_name, "url": inquiry_url})
					continue

				append_log(log_path, {"company_name": company_name, "inquiry_url": inquiry_url, "status": "submitted", "detail": ""})
				_emit({"event": "submitted", "company_name": company_name, "url": inquiry_url})
				count += 1
				time.sleep(random.uniform(sleep_min, sleep_max))
			except Exception as e:
				append_log(log_path, {"company_name": company_name, "inquiry_url": inquiry_url, "status": "failed", "detail": str(e)})
				_emit({"event": "failed", "company_name": company_name, "url": inquiry_url, "reason": str(e)})
	finally:
		try:
			driver.quit()
		except Exception:
			pass
