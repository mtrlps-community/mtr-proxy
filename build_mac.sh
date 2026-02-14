#!/bin/bash

# Check python
if ! command -v python3 &> /dev/null; then
    echo "Python3 could not be found. Please install it."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

# Clean
rm -rf dist build *.spec

# Build
echo "Building macOS application..."
pyinstaller --noconfirm --onefile --windowed --name "mtr加速器" --icon="icon.icns" main.py

# Note: You might need an icon.icns file for the app icon. 
# If not present, remove --icon="icon.icns"

echo "Build complete."
echo "App is located at dist/mtr加速器.app"
