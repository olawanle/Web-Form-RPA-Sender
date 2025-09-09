from __future__ import annotations

import os
import random
import time
from datetime import datetime
from typing import Callable, Dict, Optional

from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.common.by import By

# AI assist removed - using smart traditional form filling
from .browser import create_driver
from .captcha import is_captcha_present
from .form_filler import fill_fields, click_submit, wait_post_submit, multi_step_submit, detect_required_errors, collect_required_fields, auto_fill_remaining
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


# AI assist functions removed - using smart traditional form filling

def _ultra_aggressive_submit(driver, use_multistep_submit: bool) -> bool:
	"""ULTRA-AGGRESSIVE submit with multiple retry strategies for 100% success."""
	from .form_filler import click_submit, multi_step_submit
	
	# Strategy 1: Try normal submit
	if use_multistep_submit:
		if multi_step_submit(driver):
			return True
	else:
		if click_submit(driver):
			return True
	
	# Strategy 2: Wait and retry (for dynamic content)
	time.sleep(2)
	if use_multistep_submit:
		if multi_step_submit(driver):
			return True
	else:
		if click_submit(driver):
			return True
	
	# Strategy 3: Try JavaScript form submission
	try:
		forms = driver.find_elements(By.CSS_SELECTOR, "form")
		for form in forms:
			try:
				driver.execute_script("arguments[0].submit();", form)
				print("   ✓ Submitted form via JavaScript")
				return True
			except Exception:
				continue
	except Exception:
		pass
	
	# Strategy 4: Try pressing Enter on form elements
	try:
		from selenium.webdriver.common.keys import Keys
		form_elements = driver.find_elements(By.CSS_SELECTOR, "form input, form textarea, form select")
		for el in form_elements:
			try:
				el.send_keys(Keys.RETURN)
				print("   ✓ Pressed Enter on form element")
				return True
			except Exception:
				continue
	except Exception:
		pass
	
	# Strategy 5: Try clicking any button in forms
	forms = driver.find_elements(By.CSS_SELECTOR, "form")
	for form in forms:
		buttons = form.find_elements(By.CSS_SELECTOR, "button, input[type=button], input[type=submit], a")
		for btn in buttons:
			try:
				if btn.is_displayed() and btn.is_enabled():
					driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
					btn.click()
					print("   ✓ Clicked form button")
					return True
			except Exception:
				continue
	
	return False


def _handle_javascript_alerts(driver) -> bool:
	"""ULTRA-AGGRESSIVE JavaScript alert handling with 10+ strategies."""
	try:
		# Strategy 1: Try to handle the alert
		alert = driver.switch_to.alert
		alert_text = alert.text
		print(f"   🚨 JavaScript Alert: {alert_text}")
		
		# Handle different types of alerts
		if any(keyword in alert_text.lower() for keyword in ["送信", "submit", "確認", "confirm", "ok", "yes", "はい", "よろしい", "続行", "proceed", "送信してもよろしい", "送信してもよろしいですか"]):
			alert.accept()
			print("   ✓ Accepted positive alert")
			return True
		elif any(keyword in alert_text.lower() for keyword in ["キャンセル", "cancel", "no", "いいえ", "中止", "停止"]):
			alert.dismiss()
			print("   ✗ Dismissed negative alert")
			return False
		else:
			# Default to accept for unknown alerts
			alert.accept()
			print("   ✓ Accepted unknown alert (default)")
			return True
	except Exception as e:
		print(f"   ⚠️ Alert handling failed: {str(e)[:50]}")
		
		# Strategy 2: Try to dismiss any remaining alerts
		try:
			driver.switch_to.alert.dismiss()
			print("   ✓ Dismissed alert via fallback")
			return True
		except Exception:
			pass
		
		# Strategy 3: Try to accept any remaining alerts
		try:
			driver.switch_to.alert.accept()
			print("   ✓ Accepted alert via fallback")
			return True
		except Exception:
			pass
		
		# Strategy 4: Try to handle alerts with JavaScript
		try:
			driver.execute_script("window.alert = function() {}; window.confirm = function() { return true; }; window.prompt = function() { return true; };")
			print("   ✓ Disabled alerts via JavaScript")
			return True
		except Exception:
			pass
		
		# Strategy 5: Try to handle alerts with window.alert override
		try:
			driver.execute_script("""
				window.alert = function(msg) { console.log('Alert intercepted:', msg); };
				window.confirm = function(msg) { console.log('Confirm intercepted:', msg); return true; };
				window.prompt = function(msg) { console.log('Prompt intercepted:', msg); return true; };
			""")
			print("   ✓ Overrode alert functions via JavaScript")
			return True
		except Exception:
			pass
		
		# Strategy 6: Try to handle alerts with event listeners
		try:
			driver.execute_script("""
				window.addEventListener('beforeunload', function(e) { e.preventDefault(); });
				window.addEventListener('unload', function(e) { e.preventDefault(); });
			""")
			print("   ✓ Added event listeners to prevent alerts")
			return True
		except Exception:
			pass
		
		# Strategy 7: Try to handle alerts with timeout
		try:
			import time
			time.sleep(0.5)
			alert = driver.switch_to.alert
			alert.accept()
			print("   ✓ Accepted alert after timeout")
			return True
		except Exception:
			pass
		
		# Strategy 8: Try to handle alerts with retry
		for attempt in range(3):
			try:
				alert = driver.switch_to.alert
				alert.accept()
				print(f"   ✓ Accepted alert on attempt {attempt + 1}")
				return True
			except Exception:
				time.sleep(0.2)
				continue
		
		# Strategy 9: Try to handle alerts with different approach
		try:
			driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "body"))
			print("   ✓ Clicked body to dismiss alert")
			return True
		except Exception:
			pass
		
		# Strategy 10: Try to handle alerts with key press
		try:
			from selenium.webdriver.common.keys import Keys
			driver.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.ENTER)
			print("   ✓ Pressed Enter to dismiss alert")
			return True
		except Exception:
			pass
		
		return False


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
	# AI assist removed - using smart traditional form filling
	browser: str = "auto",
	remote_url: Optional[str] = None,
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

	driver = create_driver(browser=browser, headless=headless, remote_url=remote_url)
	count = 0
	processed_leads = []  # Track processed leads for final summary
	
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
			
			# Track this lead
			lead_result = {
				"company_name": company_name,
				"inquiry_url": inquiry_url,
				"status": "failed",
				"detail": "Processing interrupted"
			}
			
			try:
				print(f"\n🔄 Processing {count+1}/{remaining}: {company_name}")
				print(f"   URL: {inquiry_url}")
				
				try:
					# Store original URL for success detection
					driver._original_url = inquiry_url
					driver.get(inquiry_url)
				except WebDriverException as e:
					print(f"   ⚠️ WebDriver error: {str(e)[:50]}")
					try:
						driver.quit()
					except Exception:
						pass
					driver = create_driver(browser=browser, headless=headless, remote_url=remote_url)
					# Store original URL for success detection
					driver._original_url = inquiry_url
					driver.get(inquiry_url)
				except Exception as e:
					print(f"   ⚠️ General error: {str(e)[:50]}")
					try:
						driver.quit()
					except Exception:
						pass
					driver = create_driver(browser=browser, headless=headless, remote_url=remote_url)
					# Store original URL for success detection
					driver._original_url = inquiry_url
					driver.get(inquiry_url)

				_wait_dom_ready(driver, timeout=15)

				shot_loaded = ""
				if screenshot_dir:
					shot_loaded = os.path.join(screenshot_dir, f"{lead_prefix}_loaded.png")
					driver.save_screenshot(shot_loaded)
				_emit({"event": "loaded", "company_name": company_name, "url": inquiry_url, "screenshot": shot_loaded})

				if skip_on_captcha and is_captcha_present(driver):
					lead_result["status"] = "captcha_skipped"
					lead_result["detail"] = "CAPTCHA detected before fill"
					append_log(log_path, lead_result)
					_emit({"event": "captcha_skipped", "company_name": company_name, "url": inquiry_url})
					processed_leads.append(lead_result)
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
				
				print(f"   📝 Filling form fields...")
				fill_fields(driver, values, auto_consent=auto_consent)
				# Fill all remaining fields with placeholders except message
				auto_fill_remaining(driver, skip_message=True)

				# AI assist removed - using smart traditional form filling

				if preview:
					lead_result["status"] = "preview"
					lead_result["detail"] = "No submit (preview mode)"
					append_log(log_path, lead_result)
					_emit({"event": "preview", "company_name": company_name, "url": inquiry_url})
					processed_leads.append(lead_result)
					count += 1
					time.sleep(random.uniform(sleep_min, sleep_max))
					continue

				print(f"   🔍 Looking for submit button...")
				clicked = _ultra_aggressive_submit(driver, use_multistep_submit)
				
				# Handle JavaScript alerts that might appear
				if clicked:
					_handle_javascript_alerts(driver)
					# Wait a bit after handling alerts
					time.sleep(2)
					
					# Check for more alerts after waiting
					_handle_javascript_alerts(driver)
					
					# Wait for page to stabilize after alert handling
					time.sleep(1)
				
				# If required errors, try to fill missing required fields
				if (not preview) and detect_required_errors(driver):
					print(f"   ⚠️  Required field errors detected, trying to fill missing fields...")
					# Try to fill any empty required fields with smart placeholders
					required_fields = driver.find_elements(By.CSS_SELECTOR, "input[required], textarea[required], select[required]")
					for field in required_fields:
						try:
							if not field.get_attribute("value") and not field.text:
								# Generate smart placeholder based on field type and name
								field_type = field.get_attribute("type") or "text"
								field_name = (field.get_attribute("name") or "").lower()
								field_id = (field.get_attribute("id") or "").lower()
								
								placeholder = ""
								if field_type == "email" or "email" in field_name or "mail" in field_name:
									placeholder = "test@example.com"
								elif field_type == "tel" or "phone" in field_name or "tel" in field_name:
									placeholder = "03-1234-5678"
								elif "name" in field_name or "氏名" in field_name:
									placeholder = "テスト太郎"
								elif "company" in field_name or "会社" in field_name:
									placeholder = "テスト株式会社"
								elif "address" in field_name or "住所" in field_name:
									placeholder = "東京都渋谷区1-1-1"
								else:
									placeholder = "テストデータ"
								
								if placeholder:
									field.clear()
									field.send_keys(placeholder)
									print(f"   ✓ Filled required field: {field_name or field_id}")
						except Exception:
							continue
					
					# Also try to fill any empty fields that might be required
					all_fields = driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")
					for field in all_fields:
						try:
							if not field.get_attribute("value") and not field.text and field.is_displayed():
								field_type = field.get_attribute("type") or "text"
								field_name = (field.get_attribute("name") or "").lower()
								
								placeholder = ""
								if field_type == "email" or "email" in field_name or "mail" in field_name:
									placeholder = "test@example.com"
								elif field_type == "tel" or "phone" in field_name or "tel" in field_name:
									placeholder = "03-1234-5678"
								elif "name" in field_name or "氏名" in field_name:
									placeholder = "テスト太郎"
								elif "company" in field_name or "会社" in field_name:
									placeholder = "テスト株式会社"
								elif "address" in field_name or "住所" in field_name:
									placeholder = "東京都渋谷区1-1-1"
								else:
									placeholder = "テストデータ"
								
								if placeholder:
									field.clear()
									field.send_keys(placeholder)
									print(f"   ✓ Filled empty field: {field_name}")
						except Exception:
							continue
					
					# Retry submit with multiple strategies
					print(f"   🔄 Retrying submit after filling required fields...")
					clicked = clicked or _ultra_aggressive_submit(driver, use_multistep_submit)
					
					# Handle alerts again after retry
					if clicked:
						_handle_javascript_alerts(driver)
						time.sleep(2)
						_handle_javascript_alerts(driver)

				if not clicked:
					# ULTRA-AGGRESSIVE retry: Try multiple strategies before giving up
					print(f"   🔄 ULTRA-AGGRESSIVE retry: Trying all possible submission methods...")
					
					# Retry 1: Wait and try again
					time.sleep(5)
					clicked = _ultra_aggressive_submit(driver, use_multistep_submit)
					
					# Retry 2: Try JavaScript form submission directly
					if not clicked:
						try:
							forms = driver.find_elements(By.CSS_SELECTOR, "form")
							for form in forms:
								driver.execute_script("arguments[0].submit();", form)
								print("   ✓ Force submitted form via JavaScript")
								clicked = True
								break
						except Exception:
							pass
					
					# Retry 3: Try pressing Enter on all form elements
					if not clicked:
						try:
							from selenium.webdriver.common.keys import Keys
							form_elements = driver.find_elements(By.CSS_SELECTOR, "form input, form textarea, form select")
							for el in form_elements:
								try:
									el.send_keys(Keys.RETURN)
									print("   ✓ Pressed Enter on form element")
									clicked = True
									break
								except Exception:
									continue
						except Exception:
							pass
					
					# Retry 4: Try clicking any clickable element
					if not clicked:
						try:
							clickable_elements = driver.find_elements(By.CSS_SELECTOR, "button, input[type=button], input[type=submit], a, [onclick], [role=button]")
							for el in clickable_elements:
								try:
									if el.is_displayed() and el.is_enabled():
										driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
										el.click()
										print("   ✓ Clicked clickable element")
										clicked = True
										break
								except Exception as e:
									# Handle stale element reference
									if "stale element reference" in str(e).lower():
										print("   ⚠️ Stale element detected, refreshing...")
										time.sleep(1)
										continue
									continue
						except Exception:
							pass
					
					if not clicked:
						lead_result["status"] = "failed"
						lead_result["detail"] = "Submit button not found after all retry attempts"
						append_log(log_path, lead_result)
						_emit({"event": "failed", "company_name": company_name, "url": inquiry_url, "reason": "submit_not_found"})
						processed_leads.append(lead_result)
						print(f"   ❌ Failed: Submit button not found after all retry attempts")
						continue

				print(f"   ⏳ Waiting for post-submit confirmation...")
				# Try multiple success detection attempts
				submission_successful = False
				for attempt in range(5):
					print(f"   🔍 Success detection attempt {attempt + 1}/5...")
					submission_successful = wait_post_submit(driver, timeout=20)
					if submission_successful:
						break
					time.sleep(3)
					
					# Try to handle any alerts that might appear
					_handle_javascript_alerts(driver)
				shot_after = ""
				if screenshot_dir:
					shot_after = os.path.join(screenshot_dir, f"{lead_prefix}_after_submit.png")
					driver.save_screenshot(shot_after)
				_emit({"event": "submitted_wait", "company_name": company_name, "url": inquiry_url, "screenshot": shot_after})

				if skip_on_captcha and is_captcha_present(driver):
					lead_result["status"] = "captcha_skipped"
					lead_result["detail"] = "CAPTCHA after submit"
					append_log(log_path, lead_result)
					_emit({"event": "captcha_skipped", "company_name": company_name, "url": inquiry_url})
					processed_leads.append(lead_result)
					print(f"   ⚠️  CAPTCHA detected after submit")
					continue

				if not submission_successful:
					lead_result["status"] = "failed"
					lead_result["detail"] = "Form submission may have failed - no success confirmation detected"
					append_log(log_path, lead_result)
					_emit({"event": "failed", "company_name": company_name, "url": inquiry_url, "reason": "no_success_confirmation"})
					processed_leads.append(lead_result)
					print(f"   ❌ Failed: No success confirmation detected")
					continue

				lead_result["status"] = "submitted"
				lead_result["detail"] = ""
				append_log(log_path, lead_result)
				_emit({"event": "submitted", "company_name": company_name, "url": inquiry_url})
				processed_leads.append(lead_result)
				print(f"   ✅ Successfully submitted!")
				count += 1
				time.sleep(random.uniform(sleep_min, sleep_max))
				
			except Exception as e:
				lead_result["status"] = "failed"
				lead_result["detail"] = str(e)
				append_log(log_path, lead_result)
				_emit({"event": "failed", "company_name": company_name, "url": inquiry_url, "reason": str(e)})
				processed_leads.append(lead_result)
				print(f"   ❌ Error: {str(e)[:100]}")
				
	except KeyboardInterrupt:
		print(f"\n⚠️  Process interrupted by user")
		_emit({"event": "interrupted", "message": "Process stopped by user"})
	except Exception as e:
		print(f"\n❌ Unexpected error: {e}")
		_emit({"event": "error", "message": str(e)})
	finally:
		try:
			driver.quit()
		except Exception:
			pass
		
		# Always show final summary
		print(f"\n📊 FINAL SUMMARY:")
		print(f"   Total processed: {len(processed_leads)}")
		status_counts = {}
		for lead in processed_leads:
			status = lead["status"]
			status_counts[status] = status_counts.get(status, 0) + 1
		
		for status, count in status_counts.items():
			print(f"   {status}: {count}")
		
		print(f"\n📁 Log saved to: {log_path}")
		_emit({"event": "completed", "summary": status_counts, "total": len(processed_leads)})
