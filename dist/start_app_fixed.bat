@echo off
echo Starting Web Form RPA Sender...
echo.

REM Check if the virtual environment exists
if not exist "..\.venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please run the build script first to create the virtual environment.
    pause
    exit /b 1
)

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

echo Activating virtual environment...
call "..\.venv\Scripts\activate.bat"

echo Starting Streamlit application...
echo.
echo The application will open in your browser automatically.
echo To stop the application, close this window or press Ctrl+C
echo.

REM Start Streamlit with browser disabled to prevent multiple tabs
python -m streamlit run streamlit_app.py --server.port 8506 --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --server.runOnSave false

pause
