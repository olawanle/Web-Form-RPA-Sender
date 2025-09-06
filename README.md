# Web Form RPA Sender (Python + Selenium)

This tool reads a list of leads (company name + inquiry URL) from CSV/Excel, opens each URL, auto-fills common inquiry form fields, performs mail merge in the message body (e.g., "Dear XX Co., Ltd."), and sends the form. Results (success/failure/CAPTCHA skipped) are logged to a CSV. Daily submission limits and scheduled start time are supported.

## Features
- Import leads from CSV/Excel (`company_name`, `inquiry_url`, optional `contact_name`, `email`, `phone`, `subject`, `message`)
- Message templating via Jinja2 with salutation helper (`Dear Mr./Ms. ****`)
- Selenium-based form detection for common fields (name, company, email, phone, subject, message)
- Submit button detection and post-submit wait
- CAPTCHA detection with optional skip
- Logging to CSV and daily quota control
- CLI options including headless mode and scheduled start time
- Streamlit web app for no-code usage

## Installation (Windows/macOS)
1. Install Python 3.10+.
2. Install Google Chrome.
3. In a terminal, run:
```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

Optional installation as a CLI:
```bash
pip install -e .
# Then use: form-rpa --help
```

## Web App (Streamlit)

### Quick Start (Recommended)
For the easiest setup, use the batch file launcher:
```bash
# Windows
cd dist
start_app.bat

# This will:
# - Activate the virtual environment
# - Start Streamlit server
# - Open your browser automatically
# - Prevent multiple browser tabs
```

### Manual Start
Run the no-code web app manually:
```bash
streamlit run streamlit_app.py
```
- Upload your CSV/Excel and message template (or edit in the page)
- Configure options (daily cap, start time, headless, skip CAPTCHA)
- Click Run; view status updates and download the log CSV

### Required CSV Format
Your leads CSV must have these columns:
- `company_name` (required)
- `inquiry_url` (required)
- `contact_name` (optional)
- `email` (optional)
- `phone` (optional)
- `subject` (optional)

## CLI Usage
Run without installing CLI:
```bash
python -m form_rpa.cli --input sample_leads.csv \
  --template templates/message_en.txt.j2 \
  --log send_log.csv \
  --max-per-day 500 \
  --start-time "09:00" \
  --headless \
  --skip-on-captcha
```

Or with CLI after `pip install -e .`:
```bash
form-rpa --input sample_leads.csv --template templates/message_en.txt.j2 --log send_log.csv --headless --skip-on-captcha
```

## Troubleshooting

### Multiple Browser Tabs Opening
**Problem:** Application opens multiple Chrome tabs instead of one.
**Solution:** Use `start_app.bat` instead of the `.exe` file. The batch file approach prevents this issue.

### "Page Not Found" Errors
**Problem:** Browser shows "This site can't be reached" or "ERR_CONNECTION_REFUSED".
**Solution:** Ensure you're using `start_app.bat` which properly starts the Streamlit server before opening the browser.

### Missing Module Errors
**Problem:** "ModuleNotFoundError: No module named 'form_rpa'".
**Solution:** Make sure the `form_rpa` directory is in the same folder as `streamlit_app.py`.

## Notes
- Optional fields are filled only if present in your CSV/Excel.
- If a page requires CAPTCHA (reCAPTCHA/hCaptcha/Cloudflare), use `--skip-on-captcha` to skip those automatically. Full CAPTCHA solving is not included to avoid expensive services; we can integrate a solver on request.
- Duplicate sends: previously successful submissions (from `send_log.csv`) are skipped automatically.
- Daily quota: the tool counts submissions in the log made today and will send only up to `--max-per-day`.

## Deliverables
- Executable script (CLI via `form-rpa` or `python -m form_rpa.cli`)
- Streamlit web app (`streamlit_app.py`)
- This README as the operation manual

## Disclaimer
Websites differ widely. The form detection is heuristic and may need site-specific adjustments for certain targets. Provide a sample list of target domains to fine-tune selectors if required.
