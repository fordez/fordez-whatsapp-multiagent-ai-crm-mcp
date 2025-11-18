# whatsapp/agent/load_instruction.py

import logging
import time
from typing import Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from whatsapp.config import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DOC_CACHE = {}

# 🧠 Rol fijo (fallback)
DEFAULT_ROLE_PROMPT = """
Instrucciones por defecto: tu rol no fue cargado correctamente desde Google Docs.
"""


def get_google_credentials() -> Optional[Credentials]:
    """
    Devuelve las credenciales para Google Docs.
    Compatible con la estructura de config que usa service_account_json (dict).
    """
    scopes = ["https://www.googleapis.com/auth/documents.readonly"]

    try:
        # ✅ USAR service_account_json (que es un dict, no un string)
        if hasattr(config, "service_account_json") and config.service_account_json:
            logger.info(
                "[load_instruction] Usando credenciales desde service_account_json"
            )
            credentials = Credentials.from_service_account_info(
                config.service_account_json, scopes=scopes
            )
            return credentials

        # ❌ Si no hay credenciales
        logger.error("[load_instruction] No se encontró service_account_json en config")
        return None

    except Exception as e:
        logger.error(
            f"[load_instruction] Error cargando credenciales: {e}", exc_info=True
        )
        return None


def load_instructions_from_doc(
    doc_id: str, get_timestamp: bool = False
) -> Optional[str]:
    """
    Carga el contenido de un Google Doc por su ID.

    Args:
        doc_id: ID del Google Doc
        get_timestamp: Si True, devuelve el revisionId en lugar del contenido

    Returns:
        Contenido del documento o revisionId (si get_timestamp=True)
    """
    try:
        credentials = get_google_credentials()
        if not credentials:
            logger.warning(
                "[load_instruction] No hay credenciales, no se puede cargar documento"
            )
            return None

        # Construir servicio de Google Docs
        service = build("docs", "v1", credentials=credentials)

        # Obtener documento
        logger.info(
            f"[load_instruction] Solicitando documento {doc_id} a Google Docs API..."
        )
        document = service.documents().get(documentId=doc_id).execute()

        # Si solo queremos el timestamp
        if get_timestamp:
            revision_id = document.get("revisionId", str(time.time()))
            logger.info(
                f"[load_instruction] Timestamp/RevisionId obtenido: {revision_id}"
            )
            return revision_id

        # Extraer contenido del documento
        content = []
        body = document.get("body", {})

        if not body:
            logger.warning(f"[load_instruction] Documento {doc_id} no tiene body")
            return None

        for el in body.get("content", []):
            if "paragraph" in el:
                for elem in el["paragraph"].get("elements", []):
                    text_run = elem.get("textRun")
                    if text_run:
                        text = text_run.get("content", "")
                        content.append(text)

        full_content = "".join(content).strip()

        if not full_content:
            logger.warning(
                f"[load_instruction] Documento {doc_id} está vacío o solo tiene espacios"
            )
            return None

        logger.info(
            f"[load_instruction] ✅ Documento {doc_id} cargado: {len(full_content)} caracteres"
        )
        return full_content

    except Exception as e:
        logger.error(
            f"[load_instruction] ❌ Error al cargar documento {doc_id}: {e}",
            exc_info=True,
        )
        return None


async def load_instructions_for_user(role_id: str, client: dict) -> str:
    """
    Carga las instrucciones desde Google Docs usando role_id.
    Usa cache para evitar llamadas repetidas a la API.
    Si falla, devuelve DEFAULT_ROLE_PROMPT.

    Args:
        role_id: ID del documento de Google Docs con las instrucciones
        client: Diccionario con datos del cliente (no usado actualmente)

    Returns:
        String con las instrucciones del agente
    """
    if not role_id:
        logger.warning("[load_instruction] ⚠️ Role ID vacío, usando rol por defecto")
        return DEFAULT_ROLE_PROMPT

    doc_id = role_id
    logger.info(
        f"[load_instruction] 📋 Iniciando carga de instrucciones para doc_id: {doc_id}"
    )

    try:
        # 1. Obtener timestamp actual del documento
        current_timestamp = load_instructions_from_doc(doc_id, get_timestamp=True)

        if current_timestamp is None:
            logger.error(
                f"[load_instruction] ❌ No se pudo obtener timestamp del documento {doc_id}"
            )
            return DEFAULT_ROLE_PROMPT

        # 2. Verificar cache
        cached = DOC_CACHE.get(doc_id)

        if cached and cached.get("timestamp") == current_timestamp:
            logger.info(
                f"[load_instruction] ♻️ Usando cache para documento {doc_id} (sin cambios)"
            )
            return cached["data"]

        # 3. Cache miss o documento actualizado - cargar contenido
        logger.info(
            f"[load_instruction] 🔄 Cargando contenido completo desde Google Docs..."
        )
        instructions = load_instructions_from_doc(doc_id, get_timestamp=False)

        if instructions and instructions.strip():
            # Guardar en cache
            DOC_CACHE[doc_id] = {
                "data": instructions,
                "timestamp": current_timestamp,
            }
            logger.info(
                f"[load_instruction] ✅ Instrucciones cargadas y cacheadas correctamente\n"
                f"   - Documento: {doc_id}\n"
                f"   - Tamaño: {len(instructions)} caracteres\n"
                f"   - Timestamp: {current_timestamp}"
            )
            return instructions

        # Documento vacío
        logger.warning(
            f"[load_instruction] ⚠️ Documento {doc_id} está vacío, usando rol por defecto"
        )
        return DEFAULT_ROLE_PROMPT

    except Exception as e:
        logger.error(
            f"[load_instruction] ❌ Error general al cargar instrucciones: {e}",
            exc_info=True,
        )
        return DEFAULT_ROLE_PROMPT


def clear_cache(doc_id: str = None):
    """
    Limpia el cache de documentos.

    Args:
        doc_id: Si se proporciona, limpia solo ese documento.
                Si es None, limpia todo el cache.
    """
    if doc_id:
        if doc_id in DOC_CACHE:
            del DOC_CACHE[doc_id]
            logger.info(f"[load_instruction] Cache limpiado para documento {doc_id}")
    else:
        DOC_CACHE.clear()
        logger.info("[load_instruction] Cache completo limpiado")
