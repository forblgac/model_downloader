@echo off
echo Starting Model Downloader...

if not exist venv\Scripts\activate.bat (
    echo [ERROR] Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
echo Starting FastAPI Server...
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
