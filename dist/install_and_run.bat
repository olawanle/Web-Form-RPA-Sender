@echo off
echo ========================================
echo Web Form RPA Sender - Installation
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed!
    echo.
    echo Please install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    echo After installing Python, run this script again.
    pause
    exit /b 1
)

echo Python is installed! Installing required packages...
echo This may take a few minutes...
echo.

REM Install required packages
pip install -r requirements_client.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install required packages
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

echo.
echo Installation complete! Starting the application...
echo.

REM Start the application
start_app_standalone.bat
