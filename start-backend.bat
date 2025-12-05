@echo off
echo ========================================
echo Auto API Builder - Starting Backend
echo ========================================
echo.

cd backend

echo Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo.
echo Installing/Updating dependencies...
pip install -r requirements.txt

echo.
echo Starting Flask server...
echo Backend will be available at http://localhost:5001
echo.
echo Open index.html in your browser to use the application
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python server.py

pause


python -m pip install -r requirements.txt