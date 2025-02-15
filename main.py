from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from database import engine, SessionLocal
from models import Base
import csv
import io
from celery_worker import scrape_urls, celery_app
from celery.result import AsyncResult

# Initialize app
app = FastAPI()

# Create database tables
Base.metadata.create_all(bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/upload")
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = file.file.read().decode("utf-8")
    file.file.close()
    
    # Parse CSV and skip header if needed
    reader = csv.reader(io.StringIO(contents))
    urls = [row[0] for row in reader if row]
    
    # Trigger Celery task
    task = scrape_urls.delay(urls)
    return {"task_id": task.id, "message": "Scraping started."}

@app.get("/status/{task_id}")
def get_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    # Optionally, you can add more details such as result info if needed.
    if result.status == "FAILURE":
        raise HTTPException(status_code=500, detail="Task failed.")
    return {"task_id": task_id, "status": result.status}
