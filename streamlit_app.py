import io
import os
import tempfile
from datetime import datetime

import pandas as pd
import streamlit as st

from form_rpa.runner import process_leads


def main():
	st.set_page_config(page_title="Web Form RPA Sender", layout="wide")
	# Language toggle (Japanese default)
	lang = st.sidebar.radio("言語 / Language", ["日本語", "English"], index=0, horizontal=True)

	if lang == "日本語":
		title = "Webフォーム自動送信ツール"
		desc = "リード一覧とテンプレートを指定し、オプションを設定して実行してください。"
		labels = {
			"options": "オプション",
			"daily_cap": "1日の送信上限",
			"start_time": "開始時刻 (HH:MM または YYYY-MM-DD HH:MM)",
			"browser": "ブラウザ",
			"headless": "ヘッドレスブラウザ",
			"remote": "リモートWebDriver URL (任意)",
			"preview": "プレビュー (送信しない)",
			"skip_captcha": "CAPTCHA検出時はスキップ",
			"consent": "同意チェックを自動ON",
			"multistep": "確認→送信の多段階に対応",
			"min_sleep": "最小待機(秒)",
			"max_sleep": "最大待機(秒)",
			"ai_section": "AIアシスト (任意)",
			"ai_mode": "AIアシストモード",
			"ai_fill": "必須エラー時にAIで自動入力",
			"api_key": "OpenRouter APIキー",
			"leads": "リードCSV/Excel",
			"tmpl_src": "メッセージテンプレート",
			"upload": "ファイルをアップロード",
			"edit": "この画面で編集",
			"tmpl_file": "テンプレートファイル (.j2/.txt)",
			"tmpl_text": "テンプレート本文 (Jinja2)",
			"log_name": "ログファイル名",
			"run": "実行",
			"need_leads": "リードファイルをアップロードしてください。",
			"need_tmpl": "テンプレートを指定してください (アップロードまたは編集)。",
			"running": "実行中… 件数により時間がかかる場合があります。",
			"done": "完了しました。",
			"download": "ログCSVをダウンロード",
		}
		default_template = (
			"{{ salutation }}\n\n"
			"兵庫県でMEO・Web制作を行っております。{{ company_name }}様の集客や地域SEOの強化について、\n"
			"ご提案の機会をいただけますと幸いです。\n\n"
			"よろしくお願いいたします。\n"
			"担当: Your Name\n"
			"会社: Your Company\n"
		)
	else:
		title = "Web Form RPA Sender"
		desc = "Upload your leads and template, set options, then click Run."
		labels = {
			"options": "Options",
			"daily_cap": "Daily cap",
			"start_time": "Start time (HH:MM or YYYY-MM-DD HH:MM)",
			"browser": "Browser",
			"headless": "Headless browser",
			"remote": "Remote WebDriver URL (optional)",
			"preview": "Preview (no submit)",
			"skip_captcha": "Skip when CAPTCHA detected",
			"consent": "Auto-accept privacy/terms (consent)",
			"multistep": "Handle confirm→send multi-step",
			"min_sleep": "Min sleep (s)",
			"max_sleep": "Max sleep (s)",
			"ai_section": "AI Assist (Optional)",
			"ai_mode": "AI Assist Mode",
			"ai_fill": "AI: fill missing required fields on error",
			"api_key": "OpenRouter API Key",
			"leads": "Leads CSV/Excel",
			"tmpl_src": "Message template source",
			"upload": "Upload file",
			"edit": "Edit in place",
			"tmpl_file": "Template file (.j2 or .txt)",
			"tmpl_text": "Template text (Jinja2)",
			"log_name": "Log file name",
			"run": "Run",
			"need_leads": "Please upload a leads file.",
			"need_tmpl": "Please provide a message template (upload or edit in place).",
			"running": "Running... This may take a while depending on the number of leads.",
			"done": "Run completed.",
			"download": "Download full log CSV",
		}
		default_template = (
			"Dear {{ company_name }},\n\n"
			"We are reaching out from Hyogo Prefecture. We would love to discuss how we can\n"
			"help improve your local SEO and lead generation.\n\n"
			"Best regards,\n"
			"Your Name\n"
			"Your Company\n"
		)

	st.title(title)
	st.markdown(desc)

	with st.sidebar:
		st.header(labels["options"])
		max_per_day = st.number_input(labels["daily_cap"], min_value=1, max_value=100000, value=500, step=1)
		start_time = st.text_input(labels["start_time"], value="")
		browser = st.selectbox(labels["browser"], options=["auto", "chrome", "firefox"], index=0)
		headless = st.checkbox(labels["headless"], value=True)
		remote_url = st.text_input(labels["remote"], value=os.getenv("SELENIUM_REMOTE_URL", ""))
		preview = st.checkbox(labels["preview"], value=True)
		skip_captcha = st.checkbox(labels["skip_captcha"], value=True)
		auto_consent = st.checkbox(labels["consent"], value=True)
		use_multistep = st.checkbox(labels["multistep"], value=True)
		sleep_min = st.number_input(labels["min_sleep"], min_value=0.0, value=1.0, step=0.1)
		sleep_max = st.number_input(labels["max_sleep"], min_value=0.0, value=3.0, step=0.1)

		st.subheader(labels["ai_section"])
		ai_mode = st.selectbox(labels["ai_mode"], options=["off", "failure_only", "always"], index=2)
		ai_fill_required = st.checkbox(labels["ai_fill"], value=True)
		openrouter_api_key = st.text_input(labels["api_key"], value=os.getenv("OPENROUTER_API_KEY", ""), type="password")

	lead_file = st.file_uploader(labels["leads"], type=["csv", "xlsx", "xls"])
	template_src_choice = st.radio(labels["tmpl_src"], [labels["upload"], labels["edit"]], horizontal=True)
	template_file = None
	template_text = None
	if template_src_choice == labels["upload"]:
		template_file = st.file_uploader(labels["tmpl_file"], type=["j2", "txt"]) 
	else:
		template_text = st.text_area(labels["tmpl_text"], value=default_template, height=220)

	log_name = st.text_input(labels["log_name"], value=f"send_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

	col1, col2 = st.columns([2, 1])
	with col1:
		progress_area = st.empty()
		results_area = st.empty()
	with col2:
		screenshot_gallery = st.container()

	if st.button(labels["run"]):
		if not lead_file:
			st.error(labels["need_leads"])
			st.stop()
		if not template_file and not template_text:
			st.error(labels["need_tmpl"])
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

			st.info(labels["running"])

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
				browser=browser,
				remote_url=(remote_url or None),
				on_progress=on_progress,
			)

			st.success(labels["done"])
			try:
				df = pd.read_csv(log_path)
				df_display = df.tail(100)
				results_area.dataframe(df_display)
				st.download_button(labels["download"], data=open(log_path, "rb").read(), file_name=log_name, mime="text/csv")
			except Exception as e:
				st.error(f"Could not read log file: {e}")


if __name__ == "__main__":
	main()
