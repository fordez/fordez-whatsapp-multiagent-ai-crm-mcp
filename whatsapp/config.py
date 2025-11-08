import logging
import os

import pytz
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

# ====================================================
# 📘 LOGGER PROFESIONAL
# ====================================================
logger = logging.getLogger("app_logger")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logger.info("✅ Logger inicializado correctamente")

# ====================================================
# 🔑 OpenAI (Agente)
# ====================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENT_NAME = os.getenv("AGENT_NAME", "Math Tutor")

# ====================================================
# 📲 WhatsApp Cloud API (fallback global)
# ====================================================
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
APP_SECRET = os.getenv("APP_SECRET")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")

# ====================================================
# ✅ Multi Cliente desde Google Sheets
# ====================================================
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")
SHEET_NAME_LEAD = os.getenv("SHEET_NAME_LEAD")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")

# ====================================================
# 🌎 Zona horaria
# ====================================================
TIMEZONE = pytz.timezone(os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires"))


# ====================================================
# Validación opcional
# ====================================================
def validate_config():
    missing = []
    for key in [
        "OPENAI_API_KEY",
        "VERIFY_TOKEN",
        "APP_SECRET",
        "PHONE_NUMBER_ID",
        "WHATSAPP_TOKEN",
    ]:
        if not globals().get(key):
            missing.append(key)

    if missing:
        logger.warning(f"⚠️ Faltan variables en .env: {missing}")
    else:
        logger.info("✅ Configuración cargada correctamente")
