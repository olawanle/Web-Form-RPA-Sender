@echo off
setlocal enabledelayedexpansion

echo Building Web Form RPA Sender...

python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

echo Cleaning previous build...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo Building executable...
pyinstaller pyinstaller.spec --clean --noconfirm

echo Copying additional files to dist directory...
copy sample_leads.csv dist\
copy challenge.xlsx dist\
copy "問い合わせ営業　打合せ用.csv" dist\
if exist templates xcopy templates dist\templates\ /e /i

echo Build complete! Executable is at: dist\WebFormRPA.exe
echo.
echo To run the application, double-click dist\WebFormRPA.exe
pause
