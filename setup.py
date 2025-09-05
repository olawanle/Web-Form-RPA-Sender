from setuptools import setup, find_packages

setup(
	name="form_rpa",
	version="0.1.0",
	packages=find_packages(),
	install_requires=[
		"selenium>=4.12.0",
		"webdriver-manager>=4.0.0",
		"pandas>=2.0.0",
		"openpyxl>=3.1.2",
		"Jinja2>=3.1.2",
		"pydantic>=2.6.0",
		"python-dateutil>=2.8.2",
		"tenacity>=8.2.2",
	],
	entry_points={
		"console_scripts": [
			"form-rpa=form_rpa.cli:run",
		]
	},
)
