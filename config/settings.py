import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:3000")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000/api")
NOTIFICATION_INTERVAL_MINUTES = int(os.getenv("NOTIFICATION_INTERVAL_MINUTES", "10"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN must be set in environment variables")