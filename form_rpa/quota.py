from __future__ import annotations

import os
from datetime import datetime
from typing import Tuple

import pandas as pd


def count_sent_today(log_path: str) -> int:
	if not os.path.exists(log_path):
		return 0
	df = pd.read_csv(log_path)
	if df.empty or "timestamp" not in df.columns:
		return 0
	df = df[df.get("status", "").astype(str).str.lower().isin(["success", "submitted"])].copy()
	if df.empty:
		return 0
	df["date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date
	return int((df["date"] == datetime.now().date()).sum())


def remaining_quota(max_per_day: int, log_path: str) -> int:
	sent = count_sent_today(log_path)
	return max(0, max_per_day - sent)
