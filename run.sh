#!/bin/bash
echo "Starting Model Downloader..."

if [ ! -f "venv/bin/activate" ]; then
    echo "[ERROR] Virtual environment not found. Please run ./install.sh first."
    exit 1
fi

source venv/bin/activate
echo "Starting FastAPI Server..."
# Restart uvicorn dynamically
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
