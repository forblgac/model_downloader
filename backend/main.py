from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn

from .database import engine, Base, get_db, DownloadTask, DownloadStatus, init_db
from .downloader import downloader_manager

# Init DB
init_db()

app = FastAPI(title="Model Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Models
class DownloadRequest(BaseModel):
    url: str
    destination_folder: Optional[str] = "models/downloads"

class MoveTaskRequest(BaseModel):
    task_id: int
    destination_folder: str

class DownloadResponse(BaseModel):
    id: int
    url: str
    status: str
    progress_percent: float
    filename: str
    destination_folder: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

# API Routes
@app.post("/api/downloads", response_model=DownloadResponse)
async def create_download(request: DownloadRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Standardize URL
    url = request.url.strip()
    
    # Fix HuggingFace blob URLs
    if "huggingface.co" in url and "/blob/" in url:
        url = url.replace("/blob/", "/resolve/")
    
    # Simple Civitai / HuggingFace parser fallback
    # Normally we'd use hf_hub, but direct URLs are easier to handle uniformly
    
    new_task = DownloadTask(
        url=url,
        destination_folder=request.destination_folder,
        status=DownloadStatus.PENDING
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Start background download task
    background_tasks.add_task(downloader_manager.start_download, new_task.id)
    
    return new_task

@app.get("/api/downloads", response_model=List[DownloadResponse])
def get_downloads(db: Session = Depends(get_db)):
    tasks = db.query(DownloadTask).order_by(DownloadTask.created_at.desc()).all()
    return tasks

@app.delete("/api/downloads/{task_id}")
def delete_download(task_id: int, db: Session = Depends(get_db)):
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Cancel if running
    if task.status in [DownloadStatus.PENDING, DownloadStatus.DOWNLOADING]:
        downloader_manager.cancel_download(task_id)
        
    db.delete(task)
    db.commit()
    return {"status": "success"}

@app.post("/api/downloads/{task_id}/resume", response_model=DownloadResponse)
async def resume_download(task_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status in [DownloadStatus.PENDING, DownloadStatus.DOWNLOADING, DownloadStatus.COMPLETED]:
        raise HTTPException(status_code=400, detail=f"Cannot resume task in {task.status.value} state")
        
    task.status = DownloadStatus.PENDING
    task.error_message = None
    db.commit()
    db.refresh(task)
    
    background_tasks.add_task(downloader_manager.start_download, task.id)
    return task

@app.get("/api/folders")
def get_folders(path: str = None):
    import sys
    
    # If no path specified, return root drives (Windows) or root path (Unix)
    if not path:
        if sys.platform == 'win32':
            import string
            drives = []
            for letter in string.ascii_uppercase:
                if os.path.exists(f"{letter}:\\"):
                    drives.append({"name": f"{letter}:\\", "path": f"{letter}:\\", "is_dir": True})
            return drives
        else:
            path = "/"
            
    try:
        if not os.path.exists(path) or not os.path.isdir(path):
            return []
            
        folders = []
        # Add parent directory as an option if not at root
        parent = os.path.dirname(path)
        if parent != path:
            folders.append({"name": "..", "path": parent, "is_dir": True})
            
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path) and not item.startswith('.'):
                folders.append({"name": item, "path": full_path, "is_dir": True})
                
        # Sort folders alphabetically (ignoring case), with '..' always first
        sorted_folders = sorted([f for f in folders if f["name"] != ".."], key=lambda x: x['name'].lower())
        if any(f["name"] == ".." for f in folders):
            sorted_folders.insert(0, {"name": "..", "path": parent, "is_dir": True})
            
        return sorted_folders
    except Exception as e:
        # Permission denied or other errors
        return []

import shutil

@app.post("/api/move")
def move_task_file(request: MoveTaskRequest, db: Session = Depends(get_db)):
    task = db.query(DownloadTask).filter(DownloadTask.id == request.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != DownloadStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Can only move completed downloads")
        
    if not task.filename:
        raise HTTPException(status_code=400, detail="Task has no filename assigned")
        
    source_path = os.path.join(task.destination_folder, task.filename)
    dest_dir = request.destination_folder.strip()
    
    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail=f"Source file not found on disk: {source_path}")
        
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, task.filename)
    
    # Check if destination already has the file
    if os.path.exists(dest_path) and source_path != dest_path:
        raise HTTPException(status_code=400, detail=f"File already exists at destination: {dest_path}")
    
    try:
        if source_path != dest_path:
            shutil.move(source_path, dest_path)
        
        # Update database record
        task.destination_folder = dest_dir
        db.commit()
        
        return {"status": "success", "message": f"Moved {task.filename} to {dest_dir}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to move file: {str(e)}")

# Serve Frontend static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
