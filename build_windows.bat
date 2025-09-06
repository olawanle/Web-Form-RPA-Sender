@echo off
setlocal enabledelayedexpansion

python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
pyinstaller pyinstaller.spec --clean --noconfirm

echo Built dist\WebFormRPA.exe
