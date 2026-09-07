import os

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 8443))
DATA_FILE = "data.json"
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://ваш-сайт.com/webapp")