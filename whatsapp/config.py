import json
import logging
import os

import pytz
from dotenv import load_dotenv

# Cargar .env solo local
load_dotenv()

logger = logging.getLogger("whatsapp")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )


class Config:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.is_prod = self.environment == "production"

        # =========================
        # 🔐 SECRETOS GOOGLE
        # =========================
        if self.is_prod:
            # En Cloud Run los secretos llegan como JSON dentro de variables
            self.service_account_json = json.loads(os.getenv("SERVICE_ACCOUNT_FILE"))
            self.token_json = json.loads(os.getenv("TOKEN_FILE"))
        else:
            # Local: leer archivos
            with open(
                os.getenv("SERVICE_ACCOUNT_FILE", "secrets/credentials-dev.json")
            ) as f:
                self.service_account_json = json.load(f)

            with open(os.getenv("TOKEN_FILE", "secrets/token-dev.json")) as f:
                self.token_json = json.load(f)

        # =========================
        # 🌍 TIMEZONE
        # =========================
        timezone_str = os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires")
        self.timezone = pytz.timezone(timezone_str)

        # =========================
        # 🤖 OPENAI
        # =========================
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.agent_name = os.getenv("AGENT_NAME", "AG CRM Assistant")

        # =========================
        # 🔑 WHATSAPP
        # =========================
        self.verify_token = os.getenv("VERIFY_TOKEN", "fordez-token")

        # =========================
        # 📄 SHEETS CONFIG
        # =========================
        self.credentials_spreadsheet_id = os.getenv("SPREADSHEET_ID_CREDENTIALS", "")
        self.credentials_sheet_name = "Credentials"
        self.sheet_name_lead = "Lead"
        self.sheet_name_catalog = "Services"
        self.sheet_name_meetings = "Meetings"
        self.sheet_name_projects = "Projects"

        # GOOGLE SCOPES
        self.scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/spreadsheets",
        ]

        logger.info(
            "✅ Configuración cargada correctamente (modo %s)", self.environment
        )

    # =====================================================
    # 🔧 🔥 MÉTODO AÑADIDO SOLO PARA COMPATIBILIDAD
    # =====================================================
    def get_service_account_file_path(self):
        """
        Compatibilidad con módulos antiguos que esperan un archivo.
        En producción no se usa; en local sí.
        """
        return os.getenv("SERVICE_ACCOUNT_FILE", "secrets/credentials-dev.json")


# Instancia global
config = Config()
