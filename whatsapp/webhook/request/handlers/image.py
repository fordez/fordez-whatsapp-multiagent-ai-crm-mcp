import json
from config import logger

def handle_image(raw_msg: dict):
    """
    Handle incoming WhatsApp image messages.
    Parses the raw payload inline and prints the simplified object.
    """
    try:
        entry = raw_msg["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        msg = value["messages"][0]
        image = msg.get("image", {})

        # message = caption si existe, si no = "type - mime_type"
        message = image.get("caption") or f"{image.get('mime_type')}"

        parsed_data = {
            # Common info
            "account_id": entry.get("id"),
            "channel": "whatsapp",
            "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
            "contacts_name": value.get("contacts", [{}])[0].get("profile", {}).get("name"),
            "contacts_phone_number": value.get("contacts", [{}])[0].get("wa_id"),
            "message_id": msg.get("id"),
            "type": msg.get("type"),  # será 'image'
            "timestamp": msg.get("timestamp"),
            # Media info
            "filename": image.get("filename"),  # siempre None en imágenes
            "message": message,                 # caption o fallback
            "image_id": image.get("id"),
            "mime_type": image.get("mime_type"),
            "sha256": image.get("sha256"),
        }

        logger.info(f"🖼️ Parsed image message:\n{json.dumps(parsed_data, indent=2)}")

    except Exception as e:
        logger.warning(f"⚠️ Could not parse image message: {e}")
