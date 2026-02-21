# Background AI Model Downloader

A lightweight, premium Web Application that allows you to download heavy AI models (from HuggingFace, Civitai, or any direct URL) in the background. 
Designed specifically to make setting up on Windows or Mac as simple as a double-click, completely removing the need to install Node.js—everything runs securely through Python (FastAPI).

## Features

- **Double-Click Install**: No complex setups. `.bat` and `.sh` scripts handle everything from virtual environment creation to dependency installation automatically.
- **Background Downloading**: Queue multiple large files asynchronously. The UI will not block, and the downloads will stream securely in chunks.
- **Persistent Job Tracking**: Uses local SQLite. Even if you restart the server, your past successful and failed downloads remain visible.
- **Premium UI**: Dark mode, glassmorphism aesthetics, responsive floating background blobs, and smooth progress bar animations.
- **Save Anywhere**: Directly save `.safetensors` or `.ckpt` files into your specific model directories (`models/checkpoints`, `models/loras`, etc.).

## Installation

### On Windows
1. Clone or download this repository.
2. Double-click the `install.bat` file to automatically create a virtual environment and install dependencies.
3. Double-click the `run.bat` file to start the server.

### On Mac / Linux
1. Clone or download this repository.
2. Open your terminal in the directory and run:
   ```bash
   chmod +x install.sh run.sh
   ./install.sh
   ```
3. Run the application:
   ```bash
   ./run.sh
   ```

## Usage

1. Once the server is running (via `run.bat` or `./run.sh`), open your web browser.
2. Go to **`http://localhost:8000`**.
3. Paste the URL of the model you wish to download (e.g., a HuggingFace `.safetensors` direct link).
4. Select your desired destination folder.
5. Click **Start Download** and watch the progress!

## Dependencies

- Python 3.8+
- FastAPI, Uvicorn (Server & API)
- aiohttp, aiofiles (Asynchronous downloading)
- SQLAlchemy (Database modeling)

*Note: Your local download history (`downloads.db`) and destination folders are safely `.gitignore`'d and will not be pushed to GitHub.*
