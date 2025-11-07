import json
import time

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from whatsapp.config import SERVICE_ACCOUNT_FILE, SHEET_NAME, SPREADSHEET_ID, logger

# Cache en memoria
CACHE = {}
CACHE_TTL = 3600  # 1 hora


def load_sheet():
    """Carga la hoja de Google Sheet"""
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        SERVICE_ACCOUNT_FILE, scope
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    return sheet


def get_client_credentials(phone_id):
    """Obtiene todas las credenciales de un cliente según su phone_number_id"""
    now = time.time()

    # ✅ Usar cache si existe y no expiró
    if phone_id in CACHE and now - CACHE[phone_id]["ts"] < CACHE_TTL:
        logger.info(f"🟢 Usando cache para phone_id={phone_id}")
        return CACHE[phone_id]["data"]

    # ✅ Cargar desde Google Sheets
    sheet = load_sheet()
    rows = sheet.get_all_records()

    for row in rows:
        if str(row.get("Phone Number ID")) == str(phone_id):
            # Guardar toda la fila en cache
            CACHE[phone_id] = {"ts": now, "data": row}
            logger.info(
                f"🔵 Credenciales cargadas desde Sheets para phone_id={phone_id}"
            )
            # Devuelve todos los campos:
            # row = {
            #   'Business Name': ...,
            #   'Phone Number ID': ...,
            #   'Access Token': ...,
            #   'Status': ...,
            #   'Sheet CRM ID': ...,
            #   'Role Qualifier ID': ...,
            #   'Role Meeting ID': ...,
            #   'Role Tracking ID': ...
            # }
            return row

    # ⚠️ Si no encuentra credenciales, retorna None y se usará fallback
    logger.warning(
        f"⚠️ No encontré credenciales para phone_id={phone_id}, se usará fallback .env"
    )
    return None
