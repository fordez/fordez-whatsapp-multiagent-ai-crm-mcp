# whatsapp/agent/load_instruction.py

import logging
import time
from typing import Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Para credenciales en archivo o en memoria
from oauth2client.service_account import ServiceAccountCredentials

from whatsapp.config import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DOC_CACHE = {}

# 🧠 Rol fijo (fallback)
DEFAULT_ROLE_PROMPT = """
Instrucciones por defecto: tu rol no fue cargado correctamente desde Google Docs.
"""


def get_google_credentials() -> Optional[object]:
    """
    Devuelve las credenciales para Google Docs según el entorno.
    """
    scopes = ["https://www.googleapis.com/auth/documents.readonly"]

    try:
        # Producción: usa JSON en memoria
        if config.is_prod and config.service_account_json:
            logger.info("[load_instruction] Usando credenciales en memoria (prod)")
            credentials = Credentials.from_service_account_info(
                config.service_account_json, scopes=scopes
            )
            return credentials

        # Desarrollo: usa archivo local
        if config.service_account_file:
            logger.info(
                f"[load_instruction] Usando credenciales desde archivo: {config.service_account_file}"
            )
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                config.service_account_file, scopes
            )
            return credentials

        logger.error("[load_instruction] No se encontraron credenciales válidas.")
        return None
    except Exception as e:
        logger.error(f"[load_instruction] Error cargando credenciales: {e}")
        return None


def load_instructions_from_doc(
    doc_id: str, get_timestamp: bool = False
) -> Optional[str]:
    """
    Carga el contenido de un Google Doc por su ID.
    """
    try:
        credentials = get_google_credentials()
        if not credentials:
            logger.warning(
                "No se pudieron cargar las credenciales, usando rol por defecto"
            )
            return None

        service = build("docs", "v1", credentials=credentials)
        document = service.documents().get(documentId=doc_id).execute()

        if get_timestamp:
            return document.get("revisionId", str(time.time()))

        content = []
        for el in document.get("body", {}).get("content", []):
            if "paragraph" in el:
                for elem in el["paragraph"].get("elements", []):
                    text_run = elem.get("textRun")
                    if text_run:
                        content.append(text_run.get("content", ""))

        return "".join(content).strip()

    except Exception as e:
        logger.error(f"[load_instruction] Error al cargar el documento {doc_id}: {e}")
        return None


async def load_instructions_for_user(role_id: str, client: dict) -> str:
    """
    Carga las instrucciones desde Google Docs usando role_id.
    Si falla, devuelve DEFAULT_ROLE_PROMPT.
    """
    if not role_id:
        logger.warning("Role ID vacío, usando rol por defecto")
        return DEFAULT_ROLE_PROMPT

    # Usamos role_id directamente como doc_id
    doc_id = role_id
    logger.info(
        f"[load_instruction] Cargando instrucciones para role_id/doc_id: {doc_id}"
    )

    try:
        # Revisar cache
        current_timestamp = load_instructions_from_doc(doc_id, get_timestamp=True)
        cached = DOC_CACHE.get(doc_id)

        if cached and cached["timestamp"] == current_timestamp:
            logger.info(f"[load_instruction] Usando cache para documento {doc_id}")
            return cached["data"]

        # Cargar documento
        instructions = load_instructions_from_doc(doc_id, get_timestamp=False)
        if instructions and instructions.strip():
            DOC_CACHE[doc_id] = {
                "data": instructions,
                "timestamp": current_timestamp,
            }
            logger.info(
                f"[load_instruction] Instrucciones cargadas correctamente desde {doc_id}"
            )
            return instructions

        logger.warning(f"[load_instruction] Documento vacío o sin contenido ({doc_id})")
        return DEFAULT_ROLE_PROMPT

    except Exception as e:
        logger.error(f"[load_instruction] Error general al cargar instrucciones: {e}")
        return DEFAULT_ROLE_PROMPT
