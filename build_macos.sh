#!/bin/bash
# Build script for ReadIn AI on macOS

set -e

echo "=========================================="
echo "ReadIn AI - macOS Build Script"
echo "=========================================="

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This script must be run on macOS"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    echo "Install: brew install python3"
    exit 1
fi

echo ""
echo "[1/5] Installing system dependencies..."
# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install portaudio for audio capture
brew install portaudio || true

# Install BlackHole for system audio loopback (optional but recommended)
echo ""
echo "Installing BlackHole for system audio capture..."
brew install blackhole-2ch || echo "Note: BlackHole installation skipped (may already be installed)"

echo ""
echo "[2/5] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo ""
echo "[3/5] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo ""
echo "[4/5] Running platform tests..."
python test_platform.py

echo ""
echo "[5/5] Building application..."
pyinstaller --name "ReadIn AI" \
    --onefile \
    --windowed \
    --icon assets/icon.icns \
    --add-data "assets:assets" \
    --hidden-import PyQt6.QtCore \
    --hidden-import PyQt6.QtGui \
    --hidden-import PyQt6.QtWidgets \
    --hidden-import sounddevice \
    --hidden-import numpy \
    --hidden-import anthropic \
    --hidden-import faster_whisper \
    --osx-bundle-identifier com.brider.readin-ai \
    main.py

echo ""
echo "=========================================="
echo "Build complete!"
echo ""
echo "Application: dist/ReadIn AI.app"
echo ""
echo "To create a DMG installer:"
echo "  brew install create-dmg"
echo "  create-dmg --volname 'ReadIn AI' --window-size 600 400 'ReadIn AI.dmg' 'dist/ReadIn AI.app'"
echo "=========================================="
