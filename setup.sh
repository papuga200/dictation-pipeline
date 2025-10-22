#!/bin/bash
# Setup script for macOS/Linux

set -e

echo "============================================"
echo "Dictation Builder - Setup"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found!"
    echo "Please install Python 3.11+ from https://www.python.org/"
    exit 1
fi

echo "[1/3] Python found: $(python3 --version)"
echo ""

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "WARNING: FFmpeg not found!"
    echo "Please install FFmpeg:"
    echo "  macOS:   brew install ffmpeg"
    echo "  Ubuntu:  sudo apt-get install ffmpeg"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "[2/3] FFmpeg found: $(ffmpeg -version | head -n1)"
fi
echo ""

# Install Python packages
echo "[3/3] Installing Python packages..."
pip3 install -r requirements.txt

echo ""
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "To start the application:"
echo "  streamlit run app.py"
echo ""

