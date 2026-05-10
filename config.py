import os
from dotenv import load_dotenv

load_dotenv()

# API
PANDASCORE_TOKEN = os.getenv("PANDASCORE_TOKEN")

# Database
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# Sanity checks
if not PANDASCORE_TOKEN:
    raise ValueError("❌ PANDASCORE_TOKEN not found. Check your .env file.")

if not all([DB_HOST, DB_NAME, DB_USER, DB_PASS]):
    raise ValueError("❌ Database config missing. Check your .env file.")