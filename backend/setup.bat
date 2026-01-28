@echo off
REM ReadIn AI Backend - Windows Setup Script
REM This script sets up the backend server with PostgreSQL and Stripe

echo ========================================
echo  ReadIn AI Backend Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
if not exist "venv" (
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt

REM Check for .env file
echo.
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit .env file with your settings:
    echo   1. DATABASE_URL - PostgreSQL connection string
    echo   2. JWT_SECRET - Generate a secure random string
    echo   3. STRIPE_SECRET_KEY - From Stripe dashboard
    echo   4. STRIPE_WEBHOOK_SECRET - From Stripe webhook settings
    echo   5. STRIPE_PRICE_MONTHLY - Run setup_stripe.py to create
    echo.
    notepad .env
) else (
    echo .env file exists
)

echo.
echo ========================================
echo  Next Steps:
echo ========================================
echo.
echo 1. Make sure PostgreSQL is running
echo 2. Create database: createdb readin_ai
echo 3. Edit .env with your credentials
echo 4. Run: python init_db.py
echo 5. Run: python setup_stripe.py
echo 6. Start server: python main.py
echo.
pause
