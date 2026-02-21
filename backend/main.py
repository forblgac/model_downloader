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

class MoveRequest(BaseModel):
    source_path: str
    destination_folder: Optional[str] = "models/downloads"

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

import shutil

@app.post("/api/move")
def move_local_file(request: MoveRequest):
    source = request.source_path.strip()
    dest_dir = request.destination_folder.strip()
    
    if not os.path.exists(source):
        raise HTTPException(status_code=400, detail=f"Source file not found: {source}")
        
    if not os.path.isfile(source):
        raise HTTPException(status_code=400, detail=f"Source must be a file, not a directory: {source}")
        
    os.makedirs(dest_dir, exist_ok=True)
    
    filename = os.path.basename(source)
    dest_path = os.path.join(dest_dir, filename)
    
    try:
        shutil.move(source, dest_path)
        return {"status": "success", "message": f"Moved {filename} to {dest_dir}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to move file: {str(e)}")

# Serve Frontend static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
