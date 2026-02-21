@echo off
echo =========================================
echo  Model Downloader - Installation (Windows)
echo =========================================

echo 1. Creating Python Virtual Environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment. Please ensure Python is installed.
    pause
    exit /b %errorlevel%
)

echo 2. Activating Virtual Environment and installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b %errorlevel%
)

echo =========================================
echo  Installation Complete!
echo  You can now run 'run.bat' to start the app.
echo =========================================
pause
