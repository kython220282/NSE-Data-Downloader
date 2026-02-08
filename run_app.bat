@echo off
REM NSE Data Downloader - Startup Script
REM Double-click this file to run the Streamlit app

cd /d "%~dp0"
echo Starting NSE Data Downloader...
echo.

REM Use virtual environment Python if available, otherwise use system Python
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run app.py
) else (
    python -m streamlit run app.py
)

pause
