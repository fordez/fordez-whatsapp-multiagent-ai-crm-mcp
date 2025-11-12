import json
import logging
import os

import pytz
from dotenv import load_dotenv

# Cargar variables del .env
load_dotenv()

# Configurar logger
logger = logging.getLogger("whatsapp")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )


class Config:
    def __init__(self):
        # =========================
        # 🌍 AMBIENTE
        # =========================
        self.is_prod = os.getenv("ENVIRONMENT", "development") == "production"
        timezone_str = os.getenv("TIMEZONE", "America/Bogota")
        self.timezone = pytz.timezone(timezone_str)

        # =========================
        # ✅ WEBHOOK WHATSAPP
        # =========================
        self.verify_token = os.getenv("VERIFY_TOKEN", "fordez-token")

        # =========================
        # 🔑 OPENAI
        # =========================
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.agent_name = os.getenv("AGENT_NAME", "AG CRM Assistant")

        # =========================
        # 🗄️ GOOGLE SHEETS
        # =========================
        self.credentials_spreadsheet_id = os.getenv("SPREADSHEET_ID_CREDENTIALS", "")
        self.credentials_sheet_name = os.getenv("SHEET_NAME_CREDENTIALS", "Credentials")

        # Nombres de hojas estándar
        self.sheet_name_lead = os.getenv("SHEET_NAME_LEAD", "Lead")
        self.sheet_name_catalog = os.getenv("SHEET_NAME_CATALOG", "Services")
        self.sheet_name_meetings = os.getenv("SHEET_NAME_MEETINGS", "Meetings")
        self.sheet_name_projects = os.getenv("SHEET_NAME_PROJECTS", "Projects")

        # =========================
        # 🔐 GOOGLE AUTH
        # =========================
        self.scopes = [
            os.getenv("SCOPES", "https://www.googleapis.com/auth/spreadsheets")
        ]
        self.service_account_file = os.getenv(
            "SERVICE_ACCOUNT_FILE", "secrets/credentials-dev.json"
        )
        self.service_account_json = None

        if self.is_prod:
            env_json = os.getenv("SERVICE_ACCOUNT_JSON")
            if env_json:
                self.service_account_json = json.loads(env_json)
            else:
                with open(self.service_account_file) as f:
                    self.service_account_json = json.load(f)

        # Token de usuario (Google)
        token_file = os.getenv("TOKEN_FILE", "secrets/token-dev.json")
        with open(token_file) as f:
            self.token_json = json.load(f)

    # Utilidad para obtener el path del archivo de credenciales (solo en dev)
    def get_service_account_file_path(self):
        return self.service_account_file if not self.is_prod else None


# Instancia global de configuración
config = Config()
