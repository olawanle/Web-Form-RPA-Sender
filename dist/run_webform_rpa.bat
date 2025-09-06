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

REM Check if streamlit_app.py exists
if not exist "streamlit_app.py" (
    echo ERROR: streamlit_app.py not found
    echo Please ensure this file is in the same directory as this batch file.
    pause
    exit /b 1
)

REM Find an available port
set port=8506
:port_loop
netstat -an | findstr ":%port%" >nul
if %errorlevel% equ 0 (
    set /a port+=1
    goto port_loop
)

echo Using port: %port%
echo.

REM Start Streamlit
echo Starting Streamlit server...
start /b python -m streamlit run streamlit_app.py --server.port %port% --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false

REM Wait a moment for Streamlit to start
timeout /t 5 /nobreak >nul

REM Open browser
echo Opening browser...
start http://127.0.0.1:%port%

echo.
echo Web Form RPA Sender is now running!
echo.
echo To stop the application, close this window or press Ctrl+C
echo.

REM Keep the window open
pause
