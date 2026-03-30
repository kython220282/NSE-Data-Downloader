@echo off
REM NSE Data Downloader - Startup Script
REM Double-click this file to run the Streamlit app

cd /d "%~dp0"
set "APP_PATH=%CD%\app.py"
echo Starting NSE Data Downloader...
echo.

REM Use virtual environment Python if available, otherwise use system Python
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run "%APP_PATH%"
) else (
    python -m streamlit run "%APP_PATH%"
)

pause
