import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Read the DATABASE_URL from the environment variable, default to the Docker Compose value.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:denobili@db/scraping_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
