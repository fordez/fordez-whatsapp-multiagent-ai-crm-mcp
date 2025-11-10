import hashlib
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from whatsapp.config import config

# ==========================================================
# Caché de credenciales con hash para detectar cambios
# ==========================================================
CREDENTIALS_CACHE = {}  # {phone_id: {"data": dict, "hash": str, "source": str}}


def load_sheet():
    """Carga la hoja de Google Sheet de credenciales de manera segura"""
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    # Intentar cargar desde archivo de servicio
    service_account_path = getattr(config, "service_account_file", None)
    if service_account_path and os.path.isfile(service_account_path):
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            service_account_path, scope
        )
    else:
        # Intentar cargar desde JSON en memoria
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            config.service_account_json, scope
        )

    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.credentials_spreadsheet_id).worksheet(
        config.credentials_sheet_name
    )
    return sheet


def compute_row_hash(row: dict) -> str:
    """Genera un hash único de la fila para detectar cambios"""
    row_values = [str(row.get(k, "")).strip() for k in sorted(row.keys())]
    row_str = "|".join(row_values)
    return hashlib.md5(row_str.encode("utf-8")).hexdigest()


def get_client_credentials(phone_id: str) -> dict:
    """
    Obtiene las credenciales de un cliente según su phone_number_id
    usando caché basado en hash de la fila. Siempre devuelve dict.
    """
    if not phone_id:
        return {}

    try:
        sheet = load_sheet()
        rows = sheet.get_all_records()
        if not rows:
            return {}

        for row in rows:
            row_id = str(row.get("Phone Number ID") or "").strip()
            if row_id == str(phone_id).strip():
                row_hash = compute_row_hash(row)
                cached = CREDENTIALS_CACHE.get(phone_id)

                if cached and cached["hash"] == row_hash:
                    return cached["data"]

                # Cache nuevo o actualizado
                CREDENTIALS_CACHE[phone_id] = {
                    "data": row,
                    "hash": row_hash,
                    "source": "sheet",
                }
                return row

        return {}

    except Exception:
        return {}
