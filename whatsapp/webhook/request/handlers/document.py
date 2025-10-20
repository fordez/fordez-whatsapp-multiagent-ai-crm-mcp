import json
from config import logger

def handle_document(raw_msg: dict):
    """
    Handle incoming WhatsApp document messages.
    Parses the raw payload inline and prints the simplified object.
    """
    try:
        entry = raw_msg["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        msg = value["messages"][0]
        document = msg.get("document", {})

        # message = caption si existe, si no = "type - mime_type - filename"
        if document.get("caption"):
            message = document.get("caption")
        else:
            message = f" {msg.get('type')} {document.get('filename')} "

        parsed_data = {
            # Common info
            "account_id": entry.get("id"),
            "channel": "whatsapp",
            "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
            "contacts_name": value.get("contacts", [{}])[0].get("profile", {}).get("name"),
            "contacts_phone_number": value.get("contacts", [{}])[0].get("wa_id"),
            "message_id": msg.get("id"),
            "type": msg.get("type"),  # will be 'document'
            "timestamp": msg.get("timestamp"),
            # Document info first
            "filename": document.get("filename"),
            "message": message,                   # caption o default
            "document_id": document.get("id"),
            "mime_type": document.get("mime_type"),
            "sha256": document.get("sha256"),
        }

        logger.info(f"📄 Parsed document message:\n{json.dumps(parsed_data, indent=2)}")

    except Exception as e:
        logger.warning(f"⚠️ Could not parse document message: {e}")
