@echo off
echo ========================================
echo 한국은행 통화정책 분석 대시보드
echo ========================================
echo.
echo 가상환경에서 Streamlit 앱을 실행합니다...
echo.

cd /d "%~dp0"
call venv\Scripts\activate
streamlit run app.py

pause
