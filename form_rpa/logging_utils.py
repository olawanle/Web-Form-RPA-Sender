from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, List

LOG_COLUMNS = [
	"timestamp",
	"company_name",
	"inquiry_url",
	"status",
	"detail",
]


def append_log(log_path: str, row: Dict[str, str]) -> None:
	os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
	file_exists = os.path.exists(log_path)
	with open(log_path, mode="a", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
		if not file_exists:
			writer.writeheader()
		payload = {c: row.get(c, "") for c in LOG_COLUMNS}
		if not payload.get("timestamp"):
			payload["timestamp"] = datetime.now().isoformat(timespec="seconds")
		writer.writerow(payload)
