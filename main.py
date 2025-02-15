from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import csv
import io

from database import engine, SessionLocal
from models import Base  # This includes your ScrapedData model
from celery_worker import scrape_urls, celery_app
from celery.result import AsyncResult

# Import user-related models and schemas
from user_model import User
from user_schemas import UserCreate, UserOut, Token

# Import authentication utilities
from auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

# Initialize FastAPI app
app = FastAPI()

# Create database tables (this will create tables for all models registered with Base)
Base.metadata.create_all(bind=engine)

# Dependency: Get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# OAuth2 scheme configuration for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --------------------------
# Existing Endpoints
# --------------------------

@app.post("/upload")
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Read and decode the file contents
    contents = file.file.read().decode("utf-8")
    file.file.close()
    
    # Parse CSV file: this example assumes the CSV has one URL per row.
    reader = csv.reader(io.StringIO(contents))
    urls = [row[0] for row in reader if row]
    
    # Trigger the Celery task to scrape URLs asynchronously
    task = scrape_urls.delay(urls)
    return {"task_id": task.id, "message": "Scraping started."}

@app.get("/status/{task_id}")
def get_status(task_id: str):
    # Retrieve task status from Celery using the task ID
    result = AsyncResult(task_id, app=celery_app)
    if result.status == "FAILURE":
        raise HTTPException(status_code=500, detail="Task failed.")
    return {"task_id": task_id, "status": result.status}

# --------------------------
# Authentication Endpoints
# --------------------------

@app.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if the username already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Hash the user's password and create a new user record
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Authenticate the user by checking username and password
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    # Create a JWT token for the user with an expiration time
    token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

