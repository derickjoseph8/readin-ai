@echo off
echo ========================================
echo Building ReadIn AI
echo ========================================
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Step 1: Building executable with PyInstaller...
echo ----------------------------------------
pyinstaller --clean ReadInAI.spec

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo The executable is located in: dist\ReadInAI\
echo.
echo To create the installer:
echo 1. Download Inno Setup from: https://jrsoftware.org/isinfo.php
echo 2. Open installer.iss with Inno Setup
echo 3. Click Build ^> Compile (or press Ctrl+F9)
echo 4. The installer will be created in: installer_output\
echo.
echo Or run from command line if Inno Setup is in PATH:
echo   iscc installer.iss
echo.
pause
