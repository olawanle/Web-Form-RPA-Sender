from __future__ import annotations

from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


def create_chrome_driver(headless: bool = True) -> webdriver.Chrome:
	options = ChromeOptions()
	if headless:
		options.add_argument("--headless=new")
	options.add_argument("--disable-gpu")
	options.add_argument("--window-size=1400,1000")
	options.add_argument("--no-sandbox")
	options.add_argument("--disable-dev-shm-usage")
	options.add_argument("--disable-blink-features=AutomationControlled")
	options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
	options.add_experimental_option("useAutomationExtension", False)
	options.add_argument("--disable-extensions")
	options.add_argument("--disable-popup-blocking")
	options.add_argument("--lang=ja-JP")
	options.add_argument("--accept-lang=ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7")
	options.add_argument(
		"--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36"
	)
	prefs = {
		"credentials_enable_service": False,
		"profile.password_manager_enabled": False,
	}
	options.add_experimental_option("prefs", prefs)

	service = ChromeService(ChromeDriverManager().install())
	driver = webdriver.Chrome(service=service, options=options)
	driver.set_page_load_timeout(60)
	return driver
