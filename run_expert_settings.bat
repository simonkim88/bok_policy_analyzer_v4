@echo off
cd /d "%~dp0"
echo Starting Expert Settings Mode...
call venv\Scripts\activate
streamlit run src/views/settings_view.py
pause
