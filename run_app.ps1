# NSE Data Downloader - PowerShell Startup Script
# Run this script to start the Streamlit app

Write-Host "Starting NSE Data Downloader..." -ForegroundColor Green
Write-Host ""

# Change to script directory
Set-Location -Path $PSScriptRoot

# Use virtual environment Python if available, otherwise use system Python
if (Test-Path ".venv\Scripts\python.exe") {
    & ".\.venv\Scripts\python.exe" -m streamlit run app.py
} else {
    python -m streamlit run app.py
}
