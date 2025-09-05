from __future__ import annotations

from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver


KNOWN_CAPTCHA_HINTS = [
	"g-recaptcha",
	"recaptcha",
	"h-captcha",
	"hcaptcha",
	"cf-chl",
	"cloudflare",
	"turnstile",
]


def is_captcha_present(driver: WebDriver, timeout_seconds: int = 0) -> bool:
	page_source = driver.page_source.lower()
	for token in KNOWN_CAPTCHA_HINTS:
		if token in page_source:
			return True
	iframes = driver.find_elements("tag name", "iframe")
	for frame in iframes:
		src = (frame.get_attribute("src") or "").lower()
		if any(token in src for token in KNOWN_CAPTCHA_HINTS):
			return True
	return False
