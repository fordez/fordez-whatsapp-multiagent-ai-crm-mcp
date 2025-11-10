import json

from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from whatsapp.config import config  # Usar la instancia config

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
# ✅ CACHE GLOBAL DE INSTRUCCIONES
# ==========================================================
DOC_CACHE = {}  # {doc_id: {"data": str, "timestamp": str}}


# ==========================================================
# ✅ FUNCIONES AUXILIARES
# ==========================================================
def resolve_role_name(user_state: str):
    return STATE_ROLE_MAP.get(user_state)


def resolve_doc_id(role_name: str, client: dict):
    if not client or not role_name:
        return None
    return client.get(role_name)


# ==========================================================
# ✅ CARGAR INSTRUCCIONES DESDE GOOGLE DOCS
# ==========================================================
def load_instructions_from_doc(doc_id: str, get_timestamp: bool = False):
    try:
        scopes = [
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/drive.metadata.readonly",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            config.service_account_file, scopes
        )

        # Servicio para Google Docs
        docs_service = build("docs", "v1", credentials=creds)
        doc = docs_service.documents().get(documentId=doc_id).execute()

        if get_timestamp:
            # Servicio para Google Drive (obtener metadata)
            drive_service = build("drive", "v3", credentials=creds)
            file_metadata = (
                drive_service.files()
                .get(fileId=doc_id, fields="modifiedTime")
                .execute()
            )
            return file_metadata.get("modifiedTime")  # retorna string ISO

        # Construir contenido completo
        content = []
        for element in doc.get("body", {}).get("content", []):
            text_run = element.get("paragraph", {}).get("elements", [])
            for run in text_run:
                txt = run.get("textRun", {}).get("content")
                if txt:
                    content.append(txt)

        instructions = "".join(content).strip()
        return instructions

    except Exception:
        return "No se pudieron cargar las instrucciones desde Google Docs"


# ==========================================================
# ✅ CARGAR INSTRUCCIONES PARA UN USUARIO CON CACHE
# ==========================================================
async def load_instructions_for_user(user_state: str, client: dict):
    try:
        role_name = resolve_role_name(user_state)
        if not role_name:
            return "Hola, soy tu asistente."

        doc_id = resolve_doc_id(role_name, client)
        if not doc_id:
            return "Hola, soy tu asistente."

        # 1️⃣ Obtener timestamp actual del doc
        current_timestamp = load_instructions_from_doc(doc_id, get_timestamp=True)
        cached = DOC_CACHE.get(doc_id)

        if cached and cached["timestamp"] == current_timestamp:
            # 🟢 Usar caché
            return cached["data"]
        else:
            # 🔵 Refrescar desde Google Docs
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
