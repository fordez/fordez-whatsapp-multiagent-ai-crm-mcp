# whatsapp/agent/load_instruction.py

import time

from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from whatsapp.config import config

# Cache simple para no cargar siempre de Google Docs
DOC_CACHE = {}  # {role_id: {"data": str, "timestamp": str}}


async def load_instructions_for_user(role_id: str, client: dict):
    """
    Carga las instrucciones desde Google Docs usando un único Role ID.
    """
    if not role_id or not client:
        return "Hola, soy tu asistente."

    doc_id = client.get(role_id)
    if not doc_id:
        return "Hola, soy tu asistente."

    try:
        # Obtener timestamp del documento para usar cache
        current_timestamp = load_instructions_from_doc(doc_id, get_timestamp=True)
        cached = DOC_CACHE.get(doc_id)
        if cached and cached["timestamp"] == current_timestamp:
            return cached["data"]
        else:
            instructions = load_instructions_from_doc(doc_id, get_timestamp=False)
            if instructions and instructions.strip():
                DOC_CACHE[doc_id] = {
                    "data": instructions,
                    "timestamp": current_timestamp,
                }
                return instructions
            else:
                return "Hola, soy tu asistente."
    except Exception:
        return "Hola, soy tu asistente."
