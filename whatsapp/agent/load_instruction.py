# whatsapp/agent/load_instruction.py

import json

from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from whatsapp.config import SERVICE_ACCOUNT_FILE, logger

# ==========================================================
# ✅ CARGAR INSTRUCCIONES DESDE GOOGLE DOCS (SIN CACHE)
# ==========================================================


def load_instructions_from_doc(doc_id: str):
    """
    Carga las instrucciones desde un Google Docs usando Service Account
    directamente, sin usar cache.
    """
    try:
        scopes = ["https://www.googleapis.com/auth/documents.readonly"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            SERVICE_ACCOUNT_FILE, scopes
        )
        service = build("docs", "v1", credentials=creds)
        doc = service.documents().get(documentId=doc_id).execute()

        content = []
        for element in doc.get("body", {}).get("content", []):
            text_run = element.get("paragraph", {}).get("elements", [])
            for run in text_run:
                txt = run.get("textRun", {}).get("content")
                if txt:
                    content.append(txt)

        instructions = "".join(content).strip()
        logger.info(f"✅ Instructions loaded from Google Docs: {doc_id}")
        return instructions

    except Exception as e:
        logger.error(f"❌ Error loading instructions from doc {doc_id}: {e}")
        return "No se pudieron cargar las instrucciones desde Google Docs"


# ==========================================================
# ✅ MAPEO ENTRE ESTADO DEL LEAD Y ROLE
# ==========================================================

STATE_ROLE_MAP = {
    "Nuevo": "Role Qualifier ID",
    "Seguimiento": "Role Qualifier ID",
    "Interesado": "Role Meeting ID",
    "Agendado": "Role Tracking ID",
    "Negociando": "Role Tracking ID",
    "Perdido": "Role Tracking ID",
    "Activado": "Role Tracking ID",
    "Finalizado": "Role Tracking ID",
    "Recurrente": "Role Tracking ID",
}


# ==========================================================
# ✅ OBTENER ROLE NAME A PARTIR DEL ESTADO
# ==========================================================


def resolve_role_name(user_state: str):
    role = STATE_ROLE_MAP.get(user_state)
    if not role:
        logger.warning(f"No se encontró role para estado: {user_state}")
        return None

    logger.info(f"✅ Estado '{user_state}' usa role '{role}'")
    return role


# ==========================================================
# ✅ OBTENER DOC_ID A PARTIR DEL ROLE NAME Y EL CLIENT
# ==========================================================


def resolve_doc_id(role_name: str, client: dict):
    """
    role_name: Nue -> 'Role Qualifier ID'
    client: dict que contiene { "Role Qualifier ID": "...docID..." }
    """
    if not client:
        logger.warning("resolve_doc_id: client vacío")
        return None

    doc_id = client.get(role_name)

    if not doc_id:
        logger.error(f"❌ No existe doc_id para role '{role_name}' en client")
        return None

    logger.info(f"✅ Resuelto doc_id '{doc_id}' para role '{role_name}'")
    return doc_id


# ==========================================================
# ✅ FUNCIÓN PRINCIPAL PARA CARGAR INSTRUCCIONES
# ==========================================================


async def load_instructions_for_user(user_state: str, client: dict):
    """
    user_state: Ej. 'Nuevo', 'Seguimiento', 'Interesado', etc.
    client: diccionario con Role Qualifier ID, Role Meeting ID, Role Tracking ID
    """
    try:
        role_name = resolve_role_name(user_state)

        if not role_name:
            return "Hola, soy tu asistente."

        doc_id = resolve_doc_id(role_name, client)

        if not doc_id:
            return "Hola, soy tu asistente."

        return load_instructions_from_doc(doc_id)

    except Exception as e:
        logger.error(f"Error en load_instructions_for_user: {e}")
        return "Hola, soy tu asistente."
