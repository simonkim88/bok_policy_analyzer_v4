@echo off
setlocal
chcp 65001 > nul

echo ========================================
echo BOK Policy Analyzer v3 - Server Launcher
echo ========================================

cd /d "%~dp0"

:: Check for virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Creating 'venv'...
    python -m venv venv
    echo [INFO] Installing dependencies...
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

echo.
echo [INFO] Starting Streamlit App (Port 8501)...
echo [INFO] Ensure port 8501 is open in Windows Firewall.
echo.

streamlit run app.py --server.port 8501 --server.address 0.0.0.0

pause
