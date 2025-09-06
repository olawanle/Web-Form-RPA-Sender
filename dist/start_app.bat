@echo off
echo Starting Web Form RPA Sender...
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again.
    pause
    exit /b 1
)

REM Run the Python launcher
python launch_with_single_browser.py

pause