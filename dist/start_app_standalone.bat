@echo off
echo Starting Web Form RPA Sender...
echo.

REM Check if streamlit_app.py exists
if not exist "streamlit_app.py" (
    echo ERROR: streamlit_app.py not found
    echo Please ensure this file is in the same directory as this batch file.
    pause
    exit /b 1
)

REM Check if form_rpa directory exists
if not exist "form_rpa" (
    echo ERROR: form_rpa directory not found
    echo Please ensure this directory is in the same directory as this batch file.
    pause
    exit /b 1
)

echo Checking for Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo Python found! Checking for required packages...

REM Check if streamlit is installed
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required packages...
    echo This may take a few minutes on first run...
    echo.
    pip install streamlit pandas selenium webdriver-manager openpyxl jinja2 openai python-dotenv requests
    REM Check if installation was successful
    python -c "import streamlit" >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install required packages
        echo Please check your internet connection and try again
        pause
        exit /b 1
    )
    echo Packages installed successfully!
)

echo Starting Streamlit application...
echo.
echo The application will open in your browser automatically.
echo To stop the application, close this window or press Ctrl+C
echo.

REM Start Streamlit with browser disabled to prevent multiple tabs
python -m streamlit run streamlit_app.py --server.port 8506 --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --server.runOnSave false

pause
