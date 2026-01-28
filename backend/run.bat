@echo off
REM ReadIn AI Backend - Run Server
REM Starts the FastAPI server

echo Starting ReadIn AI Backend Server...
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
