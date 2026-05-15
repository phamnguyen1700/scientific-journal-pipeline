import os
from dotenv import load_dotenv

# Load variables từ file .env
load_dotenv()

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

MONGO_DB = os.getenv("MONGO_DB", "scientific_journal_tracking_db")

# OpenAlex API
OPENALEX_BASE_URL = os.getenv("OPENALEX_BASE_URL", "https://api.openalex.org")
