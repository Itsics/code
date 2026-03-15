@echo off
cd /d "%~dp0"
echo Starting Daily Movers server...
echo.
echo When you see "Running on http://127.0.0.1:5001" open that link in your browser.
echo Or open: http://localhost:5001
echo.
python -c "from app import app; app.run(host='127.0.0.1', port=5001, debug=False)"
pause
