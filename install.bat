@echo off
echo Installing ReadIn AI dependencies...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo Installing packages...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install some packages
    pause
    exit /b 1
)

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Copy .env.example to .env
echo 2. Add your ANTHROPIC_API_KEY to .env
echo 3. Run: python main.py
echo.
pause
