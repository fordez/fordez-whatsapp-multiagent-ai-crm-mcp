# whatsapp/agent/load_instruction.py
import json

from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from whatsapp.config import SERVICE_ACCOUNT_FILE, logger


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
