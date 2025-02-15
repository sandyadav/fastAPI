import os
from celery import Celery
import requests
from bs4 import BeautifulSoup
from database import SessionLocal
from models import ScrapedData
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use environment variable for Redis URL, default to the Docker Compose service name.
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
print(f"Using Redis URL: {redis_url}")  # Debug print to confirm the URL being used

celery_app = Celery(
    "tasks",
    broker=redis_url,
    backend=redis_url
)

def extract_meta(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find("title").text if soup.find("title") else ""
        description = soup.find("meta", attrs={"name": "description"})
        keywords = soup.find("meta", attrs={"name": "keywords"})
        return {
            "title": title,
            "description": description["content"] if description else "",
            "keywords": keywords["content"] if keywords else ""
        }
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return {"error": str(e)}

@celery_app.task
def scrape_urls(urls):
    db = SessionLocal()
    try:
        results = []
        for url in urls:
            metadata = extract_meta(url)
            # Extract error field if present and remove it from metadata
            error_value = metadata.pop("error", None)
            # Create the ScrapedData instance with error field explicitly set
            data_entry = ScrapedData(url=url, error=error_value, **metadata)
            db.add(data_entry)
            results.append({url: {**metadata, "error": error_value}})
        db.commit()
        return results
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        return {"error": "Database commit failed"}
    finally:
        db.close()

