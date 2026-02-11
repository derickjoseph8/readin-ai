#!/bin/bash
# Build script for ReadIn AI on Linux

set -e

echo "=========================================="
echo "ReadIn AI - Linux Build Script"
echo "=========================================="

# Check if we're on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "Error: This script must be run on Linux"
    exit 1
fi

# Detect package manager
if command -v apt &> /dev/null; then
    PKG_MANAGER="apt"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
else
    echo "Warning: Unknown package manager. You may need to install dependencies manually."
    PKG_MANAGER="unknown"
fi

echo "Package manager: $PKG_MANAGER"

echo ""
echo "[1/5] Installing system dependencies..."
case $PKG_MANAGER in
    apt)
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv \
            portaudio19-dev python3-pyaudio \
            libxcb-xinerama0 libxcb-cursor0 \
            pulseaudio pulseaudio-utils
        ;;
    dnf)
        sudo dnf install -y python3 python3-pip python3-virtualenv \
            portaudio-devel \
            pulseaudio pulseaudio-utils
        ;;
    pacman)
        sudo pacman -Sy --noconfirm python python-pip python-virtualenv \
            portaudio \
            pulseaudio pulseaudio-alsa
        ;;
    *)
        echo "Please install: python3, pip, portaudio-dev, pulseaudio"
        ;;
esac

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
pyinstaller --name "ReadInAI" \
    --onefile \
    --windowed \
    --add-data "assets:assets" \
    --hidden-import PyQt6.QtCore \
    --hidden-import PyQt6.QtGui \
    --hidden-import PyQt6.QtWidgets \
    --hidden-import sounddevice \
    --hidden-import numpy \
    --hidden-import anthropic \
    --hidden-import faster_whisper \
    main.py

echo ""
echo "=========================================="
echo "Build complete!"
echo ""
echo "Executable: dist/ReadInAI"
echo ""
echo "To create a .desktop file for the app menu:"
cat << 'EOF'
[Desktop Entry]
Type=Application
Name=ReadIn AI
Comment=AI Meeting Assistant
Exec=/path/to/ReadInAI
Icon=readin-ai
Terminal=false
Categories=Utility;AudioVideo;
EOF
echo ""
echo "To create an AppImage (optional):"
echo "  pip install appimage-builder"
echo "  appimage-builder --recipe AppImageBuilder.yml"
echo "=========================================="
