from sqlalchemy import Column, Integer, String
from database import Base

class ScrapedData(Base):
    __tablename__ = "scraped_data"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    title = Column(String)
    description = Column(String)
    keywords = Column(String)
    error = Column(String, nullable=True)  # New column for storing errors
