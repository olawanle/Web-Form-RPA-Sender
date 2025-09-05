import io
import os
import tempfile
from datetime import datetime

import pandas as pd
import streamlit as st

from form_rpa.runner import process_leads


def main():
	st.set_page_config(page_title="Web Form RPA Sender", layout="wide")
	st.title("Web Form RPA Sender")
	st.markdown("Upload your leads file and message template, set options, and click Run.")

	with st.sidebar:
		st.header("Options")
		max_per_day = st.number_input("Daily cap", min_value=1, max_value=100000, value=500, step=1)
		start_time = st.text_input("Start time (HH:MM or YYYY-MM-DD HH:MM)", value="")
		headless = st.checkbox("Headless browser", value=True)
		preview = st.checkbox("Preview (no submit)", value=True)
		skip_captcha = st.checkbox("Skip when CAPTCHA detected", value=True)
		auto_consent = st.checkbox("Auto-accept privacy/terms (consent)", value=True)
		use_multistep = st.checkbox("Handle confirm→send multi-step", value=True)
		sleep_min = st.number_input("Min sleep (s)", min_value=0.0, value=1.0, step=0.1)
		sleep_max = st.number_input("Max sleep (s)", min_value=0.0, value=3.0, step=0.1)

		st.subheader("AI Assist (Optional)")
		ai_mode = st.selectbox("AI Assist Mode", options=["off", "failure_only", "always"], index=2)
		ai_fill_required = st.checkbox("AI: fill missing required fields on error", value=True)
		openrouter_api_key = st.text_input("OpenRouter API Key", value=os.getenv("OPENROUTER_API_KEY", ""), type="password")

	lead_file = st.file_uploader("Leads CSV/Excel", type=["csv", "xlsx", "xls"])
	template_src_choice = st.radio("Message template source", ["Upload file", "Edit in place"], horizontal=True)
	template_file = None
	template_text = None
	if template_src_choice == "Upload file":
		template_file = st.file_uploader("Template file (.j2 or .txt)", type=["j2", "txt"]) 
	else:
		default_template = "Dear {{ company_name }},\n\nWe are reaching out from Hyogo Prefecture...\n\nBest regards,\nYour Name\nYour Company\n"
		template_text = st.text_area("Template text (Jinja2)", value=default_template, height=220)

	log_name = st.text_input("Log file name", value=f"send_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

	col1, col2 = st.columns([2, 1])
	with col1:
		progress_area = st.empty()
		results_area = st.empty()
	with col2:
		screenshot_gallery = st.container()

	if st.button("Run"):
		if not lead_file:
			st.error("Please upload a leads file.")
			st.stop()
		if not template_file and not template_text:
			st.error("Please provide a message template (upload or edit in place).")
			st.stop()

		with tempfile.TemporaryDirectory() as tmpdir:
			lead_path = os.path.join(tmpdir, lead_file.name)
			with open(lead_path, "wb") as f:
				f.write(lead_file.read())

			if template_file is not None:
				template_path = os.path.join(tmpdir, template_file.name)
				with open(template_path, "wb") as f:
					f.write(template_file.read())
			else:
				template_path = os.path.join(tmpdir, "template.txt.j2")
				with open(template_path, "w", encoding="utf-8") as f:
					f.write(template_text or "")

			log_path = os.path.join(tmpdir, log_name)
			shot_dir = os.path.join(tmpdir, "screenshots")

			st.info("Running... This may take a while depending on the number of leads.")

			def on_progress(ev: dict):
				event = ev.get("event", "")
				company = ev.get("company_name", "")
				url = ev.get("url", "")
				screenshot = ev.get("screenshot", "")
				progress_area.write(f"{event}: {company} - {url}")
				if screenshot and os.path.exists(screenshot):
					with screenshot_gallery:
						st.image(screenshot, caption=os.path.basename(screenshot), use_container_width=True)

			process_leads(
				input_path=lead_path,
				template_path=template_path,
				log_path=log_path,
				max_per_day=int(max_per_day),
				start_time=start_time or None,
				headless=bool(headless),
				preview=bool(preview),
				skip_on_captcha=bool(skip_captcha),
				sleep_min=float(sleep_min),
				sleep_max=float(sleep_max),
				screenshot_dir=shot_dir,
				auto_consent=bool(auto_consent),
				use_multistep_submit=bool(use_multistep),
				ai_assist_mode=ai_mode,
				openrouter_api_key=(openrouter_api_key or None),
				ai_fill_required=bool(ai_fill_required),
				on_progress=on_progress,
			)

			st.success("Run completed.")
			try:
				df = pd.read_csv(log_path)
				df_display = df.tail(100)
				results_area.dataframe(df_display)
				st.download_button("Download full log CSV", data=open(log_path, "rb").read(), file_name=log_name, mime="text/csv")
			except Exception as e:
				st.error(f"Could not read log file: {e}")


if __name__ == "__main__":
	main()
