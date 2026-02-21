import asyncio
import os
import aiofiles
import aiohttp
from urllib.parse import urlparse
import re
from typing import Optional
from sqlalchemy.orm import Session
from .database import SessionLocal, DownloadTask, DownloadStatus

class DownloadManager:
    def __init__(self):
        self.active_tasks = {} # task_id -> asyncio.Task

    async def start_download(self, task_id: int):
        db: Session = SessionLocal()
        task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
        if not task:
            db.close()
            return
        
        task.status = DownloadStatus.DOWNLOADING
        db.commit()
        
        async_task = asyncio.create_task(self._download_coroutine(task_id, task.url, task.destination_folder))
        self.active_tasks[task_id] = async_task
        db.close()

    def cancel_download(self, task_id: int):
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            del self.active_tasks[task_id]
            
            db: Session = SessionLocal()
            task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
            if task:
                task.status = DownloadStatus.CANCELLED
                db.commit()
            db.close()

    async def _download_coroutine(self, task_id: int, url: str, destination_folder: str):
        db: Session = SessionLocal()
        task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
        
        try:
            os.makedirs(destination_folder, exist_ok=True)
            
            file_path = ""
            file_size = 0
            headers = {}
            
            if task.filename:
                file_path = os.path.join(destination_folder, task.filename)
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    if file_size > 0:
                        headers["Range"] = f"bytes={file_size}-"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, allow_redirects=True) as response:
                    if response.status == 416:
                        task.status = DownloadStatus.COMPLETED
                        task.progress_percent = 100.0
                        task.downloaded_bytes = task.total_bytes
                        return
                        
                    response.raise_for_status()
                    
                    # Extract filename if not present
                    if not task.filename:
                        filename = self._extract_filename(response, url)
                        task.filename = filename
                        db.commit()
                        file_path = os.path.join(destination_folder, filename)
                    
                    is_resume = response.status == 206
                    if not is_resume:
                        file_size = 0
                        mode = 'wb'
                    else:
                        mode = 'ab'
                    
                    content_length = int(response.headers.get('content-length', 0))
                    total_size = file_size + content_length
                    task.total_bytes = total_size
                    db.commit()
                    
                    downloaded_size = file_size
                    chunk_size = 1024 * 1024 * 2  # 2MB chunks
                    
                    async with aiofiles.open(file_path, mode=mode) as f:
                        async for data in response.content.iter_chunked(chunk_size):
                            await f.write(data)
                            downloaded_size += len(data)
                            
                            # Update DB periodically
                            if total_size > 0:
                                current_percent = (downloaded_size / total_size) * 100
                                if current_percent - task.progress_percent >= 1.0 or downloaded_size == total_size:
                                    task.downloaded_bytes = downloaded_size
                                    task.progress_percent = current_percent
                                    db.commit()
                            else:
                                task.downloaded_bytes = downloaded_size
                                db.commit()
                    
            task.status = DownloadStatus.COMPLETED
            task.progress_percent = 100.0
            
        except asyncio.CancelledError:
            task.status = DownloadStatus.CANCELLED
            task.error_message = "Download cancelled by user"
        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)
        finally:
            db.commit()
            db.close()
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

    def _extract_filename(self, response: aiohttp.ClientResponse, url: str) -> str:
        # Check Content-Disposition
        cd = response.headers.get('Content-Disposition')
        if cd:
            # e.g., attachment; filename="model.safetensors"
            match = re.search(r'filename="?([^";]+)"?', cd)
            if match:
                return match.group(1)
        
        # Fallback to URL path
        parsed_url = urlparse(url)
        path = parsed_url.path
        filename = os.path.basename(path)
        
        if not filename:
            filename = "downloaded_file.bin"
            
        return filename

downloader_manager = DownloadManager()
