from __future__ import annotations

import os
from typing import Dict, List, Optional

from openai import OpenAI


DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_BASE = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")


def _client(api_key: Optional[str]) -> OpenAI:
	key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
	if not key:
		raise ValueError("Missing OpenRouter/OpenAI API key")
	return OpenAI(api_key=key, base_url=OPENROUTER_BASE)


PROMPT = (
	"You are an automation assistant. Given an HTML snippet from a Japanese contact page, "
	"output a JSON object mapping logical fields to robust CSS selectors. Keys: name, company, email, phone, subject, message, submit, consents (array). "
	"Be conservative and prefer label/placeholder/id-based selectors. If a field is not present, omit it."
)


def suggest_selectors(html_snippet: str, api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, object]:
	client = _client(api_key)
	model_id = model or DEFAULT_MODEL
	messages = [
		{"role": "system", "content": PROMPT},
		{"role": "user", "content": f"HTML:\n{html_snippet[:20000]}"},
	]
	resp = client.chat.completions.create(
		model=model_id,
		messages=messages,
		temperature=0.1,
	)
	content = resp.choices[0].message.content or "{}"
	import json
	try:
		start = content.find("{")
		end = content.rfind("}")
		if start != -1 and end != -1:
			content = content[start:end+1]
		return json.loads(content)
	except Exception:
		return {}


VALUE_PROMPT_SYSTEM = (
	"You help fill required fields on Japanese contact forms.\n"
	"Given a JSON array of required fields (each with key, label, placeholder, name, id, type), and a context (company_name, contact_name),\n"
	"return a JSON object where keys are the provided 'key' values and values are strings to input.\n"
	"Rules: Use Japanese where appropriate. Use realistic placeholders (e.g., 氏名=山田 太郎, 会社名=株式会社サンプル, 電話=050-1234-5678, メール=info@example.com).\n"
	"Never include newlines in values; keep them short. If unsure, provide a reasonable default."
)


def generate_values(required_fields: List[Dict[str, str]], context: Dict[str, str], api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, str]:
	if not required_fields:
		return {}
	client = _client(api_key)
	model_id = model or DEFAULT_MODEL
	import json
	payload = {
		"required_fields": required_fields[:50],
		"context": {k: context.get(k, "") for k in ["company_name", "contact_name"]},
	}
	messages = [
		{"role": "system", "content": VALUE_PROMPT_SYSTEM},
		{"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
	]
	resp = client.chat.completions.create(
		model=model_id,
		messages=messages,
		temperature=0.2,
	)
	content = resp.choices[0].message.content or "{}"
	try:
		start = content.find("{")
		end = content.rfind("}")
		if start != -1 and end != -1:
			content = content[start:end+1]
		return json.loads(content)
	except Exception:
		return {}
