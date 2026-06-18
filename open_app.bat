@echo off
setlocal

cd /d "%~dp0"

echo Starting AI Trading Bot dashboard...
echo.

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Failed to install requirements. Please check Python and pip.
    pause
    exit /b 1
)

echo.
echo Opening dashboard at http://localhost:8501
echo Press Ctrl+C in this window to stop the app.
echo.

python -m streamlit run src\dashboard\app.py

pause
