#!/bin/bash
echo "========================================="
echo " Model Downloader - Installation (Mac/Linux)"
echo "========================================="

echo "1. Creating Python Virtual Environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to create virtual environment. Please ensure Python 3 is installed."
    exit 1
fi

echo "2. Activating Virtual Environment and installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    exit 1
fi

echo "========================================="
echo " Installation Complete!"
echo " You can now run './run.sh' to start the app."
echo "========================================="
