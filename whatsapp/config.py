# whatsapp/config.py
import json
import logging
import os

import pytz
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

# Logger
logger = logging.getLogger("whatsapp")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )


class Config:
    def __init__(self):
        self.is_prod = os.getenv("ENVIRONMENT", "development") == "production"

        # OpenAI
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.agent_name = os.getenv("AGENT_NAME", "AG CRM Assistant")

        # Google Sheets
        self.scopes = [
            os.getenv("SCOPES", "https://www.googleapis.com/auth/spreadsheets")
        ]

        # Servicio account
        self.service_account_file = os.getenv(
            "SERVICE_ACCOUNT_FILE", "secrets/credentials-dev.json"
        )
        self.service_account_json = None
        if self.is_prod:
            # En producción, opcionalmente pasar JSON literal en ENV
            env_json = os.getenv("SERVICE_ACCOUNT_JSON")
            if env_json:
                self.service_account_json = json.loads(env_json)
            else:
                # Si no, cargar desde archivo
                with open(self.service_account_file) as f:
                    self.service_account_json = json.load(f)

        # Google Calendar
        token_file = os.getenv("TOKEN_FILE", "secrets/token-dev.json")
        with open(token_file) as f:
            self.token_json = json.load(f)

        # Hoja de credenciales
        self.credentials_spreadsheet_id = os.getenv("SPREADSHEET_ID_CREDENTIALS")
        self.credentials_sheet_name = os.getenv("SHEET_NAME_CREDENTIALS", "Credentials")

        # Hojas de servicios
        self.spreadsheet_id_services = os.getenv("SPREADSHEET_ID_SERVICES")
        self.sheet_name_lead = os.getenv("SHEET_NAME_LEAD", "Lead")
        self.sheet_name_catalog = os.getenv("SHEET_NAME_CATALOG", "Services")
        self.sheet_name_meetings = os.getenv("SHEET_NAME_MEETINGS", "Meetings")
        self.sheet_name_projects = os.getenv("SHEET_NAME_PROJECTS", "Projects")

        # Timezone
        timezone_str = os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires")
        self.timezone = pytz.timezone(timezone_str)

    def get_service_account_file_path(self):
        return self.service_account_file if not self.is_prod else None


# Instancia global
config = Config()
