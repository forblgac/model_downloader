import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Enum, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import enum
from datetime import datetime

DATABASE_URL = "sqlite:///./downloads.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class DownloadStatus(str, enum.Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class DownloadTask(Base):
    __tablename__ = "download_tasks"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    status = Column(Enum(DownloadStatus), default=DownloadStatus.PENDING)
    progress_percent = Column(Float, default=0.0)
    downloaded_bytes = Column(Integer, default=0)
    total_bytes = Column(Integer, default=0)
    filename = Column(String, default="")
    destination_folder = Column(String, default="models/downloads")
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
