@echo off
echo ============================================
echo   ReadIn AI - Speaker Diarization Installer
echo ============================================
echo.
echo This will install the optional speaker diarization feature.
echo It allows ReadIn AI to identify WHO is speaking in meetings.
echo.
echo Requirements:
echo   - About 2GB of disk space
echo   - Internet connection
echo   - May take 5-10 minutes
echo.
pause

echo.
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo [2/3] Installing PyTorch (AI framework)...
echo This may take a few minutes...
pip install torch --quiet

if errorlevel 1 (
    echo ERROR: Failed to install PyTorch.
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo [3/3] Installing pyannote.audio (speaker recognition)...
pip install pyannote.audio --quiet

if errorlevel 1 (
    echo ERROR: Failed to install pyannote.audio.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo Next steps:
echo   1. Open ReadIn AI
echo   2. Go to Settings ^> Speakers tab
echo   3. Enter your HuggingFace token
echo   4. Enable Speaker Diarization
echo.
echo To get a HuggingFace token:
echo   1. Create account at https://huggingface.co
echo   2. Go to Settings ^> Access Tokens ^> New token
echo   3. Accept license at https://huggingface.co/pyannote/speaker-diarization-3.1
echo.
pause
