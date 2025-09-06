from __future__ import annotations

from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


def create_driver(
	browser: str = "auto",
	headless: bool = True,
	remote_url: Optional[str] = None,
) -> webdriver.Remote:
	"""Create a WebDriver instance.

	browser: 'chrome' | 'firefox' | 'auto'
	remote_url: If provided, connect to a Selenium Grid/Remote.
	"""
	if remote_url:
		if browser in ("auto", "chrome"):
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
			driver = webdriver.Remote(command_executor=remote_url, options=options)
			driver.set_page_load_timeout(60)
			return driver
		else:
			fo = FirefoxOptions()
			if headless:
				fo.add_argument("-headless")
			driver = webdriver.Remote(command_executor=remote_url, options=fo)
			driver.set_page_load_timeout(60)
			return driver

	# Local drivers
	last_err = None
	if browser in ("auto", "chrome"):
		try:
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
			service = ChromeService(ChromeDriverManager().install())
			driver = webdriver.Chrome(service=service, options=options)
			driver.set_page_load_timeout(60)
			return driver
		except Exception as e:
			last_err = e

	# Fallback to Firefox
	fo = FirefoxOptions()
	if headless:
		fo.add_argument("-headless")
	service = FirefoxService(GeckoDriverManager().install())
	driver = webdriver.Firefox(service=service, options=fo)
	driver.set_page_load_timeout(60)
	return driver
