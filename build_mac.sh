#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt pyinstaller
pyinstaller pyinstaller.spec --clean --noconfirm

echo "Built dist/WebFormRPA"
