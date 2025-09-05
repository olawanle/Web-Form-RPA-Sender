from __future__ import annotations

import argparse

from .runner import process_leads


def parse_args() -> argparse.Namespace:
	p = argparse.ArgumentParser(description="Web form sender")
	p.add_argument("--input", required=True, help="Path to leads CSV/Excel")
	p.add_argument("--template", required=True, help="Path to message template (Jinja2)")
	p.add_argument("--log", default="send_log.csv", help="Path to output log CSV")
	p.add_argument("--max-per-day", type=int, default=500, help="Daily send limit")
	p.add_argument("--start-time", default=None, help="Start time 'YYYY-MM-DD HH:MM' or 'HH:MM'")
	p.add_argument("--headless", action="store_true", help="Run headless Chrome")
	p.add_argument("--skip-on-captcha", action="store_true", help="Skip if CAPTCHA detected")
	p.add_argument("--sleep-min", type=float, default=1.0, help="Min seconds between sends")
	p.add_argument("--sleep-max", type=float, default=3.0, help="Max seconds between sends")
	p.add_argument("--preview", action="store_true", help="Preview mode: fill but do not submit")
	p.add_argument("--screenshot-dir", default=None, help="Directory to save screenshots")
	p.add_argument("--no-consent", action="store_true", help="Do not auto-accept privacy/terms checkboxes")
	p.add_argument("--no-multistep", action="store_true", help="Disable multi-step confirm→send handling")
	p.add_argument("--ai-assist", choices=["off", "failure_only", "always"], default="off", help="Use AI to infer selectors")
	p.add_argument("--openrouter-api-key", default=None, help="OpenRouter API key (or set OPENROUTER_API_KEY env var)")
	return p.parse_args()


def run() -> None:
	args = parse_args()
	process_leads(
		input_path=args.input,
		template_path=args.template,
		log_path=args.log,
		max_per_day=args.max_per_day,
		start_time=args.start_time,
		headless=args.headless,
		skip_on_captcha=args.skip_on_captcha,
		sleep_min=args.sleep_min,
		sleep_max=args.sleep_max,
		preview=args.preview,
		screenshot_dir=args.screenshot_dir,
		auto_consent=(not args.no_consent),
		use_multistep_submit=(not args.no_multistep),
		ai_assist_mode=args.ai_assist,
		openrouter_api_key=args.openrouter_api_key,
	)


if __name__ == "__main__":
	run()
