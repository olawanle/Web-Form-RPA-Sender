from __future__ import annotations

import os
from typing import Dict, List, Tuple

import pandas as pd

REQUIRED_COLUMNS = ["company_name", "inquiry_url"]
OPTIONAL_COLUMNS = [
	"contact_name",
	"email",
	"phone",
	"subject",
	"message",
]


_JP_INQUIRY_TOKENS = [
	"問い合わせ", "お問い", "お問合せ", "問合", "コンタクト", "contact", "inquiry"
]
_JP_COMPANY_TOKENS = [
	"会社", "社名", "企業", "company"
]
_JP_NAME_TOKENS = [
	"氏名", "お名前", "担当", "担当者", "name"
]
_JP_EMAIL_TOKENS = [
	"メール", "mail", "email", "e-mail"
]
_JP_PHONE_TOKENS = [
	"電話", "tel", "phone"
]
_JP_SUBJECT_TOKENS = [
	"件名", "題名", "subject"
]
_JP_MESSAGE_TOKENS = [
	"お問い合わせ内容", "お問い合わせ", "内容", "本文", "message", "inquiry"
]


def _read_csv_any_encoding(input_path: str) -> pd.DataFrame:
	last_err: Exception | None = None
	for enc in ["utf-8", "utf-8-sig", "cp932", "shift_jis", "sjis", "ms932"]:
		try:
			return pd.read_csv(input_path, encoding=enc)
		except Exception as e:
			last_err = e
	raise last_err or ValueError("Unable to read CSV with common encodings")


def _read_tabular(input_path: str) -> pd.DataFrame:
	_, ext = os.path.splitext(input_path.lower())
	if ext in [".csv", ".txt"]:
		return _read_csv_any_encoding(input_path)
	if ext in [".xlsx", ".xlsm", ".xls"]:
		return pd.read_excel(input_path)
	raise ValueError(f"Unsupported file type: {ext}")


def _contains_any(text: str, tokens: List[str]) -> bool:
	low = text.lower()
	if any(t in low for t in tokens):
		return True
	return any(t in text for t in tokens)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
	cols = list(df.columns)
	jp_inquiry_candidates: List[str] = []
	generic_url_cols: List[str] = []
	rename_map: Dict[str, str] = {}
	company_candidates: List[str] = []

	for c in cols:
		c_str = str(c)
		c_low = c_str.lower()
		if _contains_any(c_str, _JP_INQUIRY_TOKENS):
			jp_inquiry_candidates.append(c)
			continue
		if c_low == "url":
			generic_url_cols.append(c)
			continue
		if _contains_any(c_str, _JP_COMPANY_TOKENS):
			company_candidates.append(c)
			continue
		if _contains_any(c_str, _JP_NAME_TOKENS):
			rename_map[c] = "contact_name"
			continue
		if _contains_any(c_str, _JP_EMAIL_TOKENS):
			rename_map[c] = "email"
			continue
		if _contains_any(c_str, _JP_PHONE_TOKENS):
			rename_map[c] = "phone"
			continue
		if _contains_any(c_str, _JP_SUBJECT_TOKENS):
			rename_map[c] = "subject"
			continue
		if _contains_any(c_str, _JP_MESSAGE_TOKENS):
			rename_map[c] = "message"
			continue

	# Decide inquiry_url
	if jp_inquiry_candidates:
		primary_inq = jp_inquiry_candidates[0]
		rename_map[primary_inq] = "inquiry_url"
		# Preserve generic URL as website_url
		for u in generic_url_cols:
			rename_map[u] = "website_url"
	elif generic_url_cols:
		# Fall back to generic URL as inquiry_url
		rename_map[generic_url_cols[0]] = "inquiry_url"
		for extra in generic_url_cols[1:]:
			rename_map[extra] = "website_url"

	# Company name
	if company_candidates:
		rename_map[company_candidates[0]] = "company_name"
	# Fallback: if no company_name, use the first non-url column as company_name
	if "company_name" not in rename_map.values():
		for c in cols:
			if c in jp_inquiry_candidates or c in generic_url_cols:
				continue
			if c in rename_map:
				continue
			rename_map[c] = "company_name"
			break

	if rename_map:
		df = df.rename(columns=rename_map)
	return df


def load_leads(input_path: str) -> pd.DataFrame:
	data = _read_tabular(input_path)
	data = _normalize_columns(data)
	data.columns = [str(c).strip().lower() for c in data.columns]
	missing = [col for col in REQUIRED_COLUMNS if col not in data.columns]
	if missing:
		raise ValueError(
			f"Missing required column(s) {missing}. Accepts Japanese headers (e.g., '問い合わせURL', '会社名')."
		)
	for col in OPTIONAL_COLUMNS:
		if col not in data.columns:
			data[col] = ""
	data = data.fillna("")
	data = data.drop_duplicates(subset=["inquiry_url", "company_name"], keep="first")
	return data


def dedupe_against_log(
	leads: pd.DataFrame,
	log_path: str,
	dedupe_on: List[str] | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
	if dedupe_on is None:
		dedupe_on = ["inquiry_url", "company_name"]
	if not os.path.exists(log_path):
		return leads, pd.DataFrame(columns=leads.columns)
	log_df = pd.read_csv(log_path)
	log_df.columns = [c.strip().lower() for c in log_df.columns]
	if "status" not in log_df.columns:
		return leads, pd.DataFrame(columns=leads.columns)
	sent = log_df[log_df["status"].str.lower().isin(["success", "submitted"])].copy()
	if sent.empty:
		return leads, pd.DataFrame(columns=leads.columns)
	key = dedupe_on[0] if len(dedupe_on) == 1 else dedupe_on
	remaining = leads.merge(
		sent[key], how="left", on=key, indicator=True
	)
	remaining = remaining[remaining["_merge"] == "left_only"].drop(columns=["_merge"]) 
	removed = leads.merge(
		sent[key].drop_duplicates(), how="inner", on=key
	)
	return remaining, removed
