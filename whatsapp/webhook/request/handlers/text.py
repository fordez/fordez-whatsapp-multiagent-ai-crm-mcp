import json
from config import logger

def handle_text(raw_data: dict):
    """
    Extrae toda la información del primer mensaje de texto del raw_data directamente.
    """

    try:
        entry = raw_data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        msg = value["messages"][0]

        # Información del mensaje
        parsed_message = {
            "account_id": entry.get("id"),
            "channel": "whatsapp",
            "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
            "contacts_name": value.get("contacts", [{}])[0].get("profile", {}).get("name"),
            "contacts_phone_number": value.get("contacts", [{}])[0].get("wa_id"),
            "message_id": msg.get("id"),
            "from": msg.get("from"),
            "type": msg.get("type"),  # Tipo real
            "message": msg.get("text", {}).get("body"),
            "timestamp": msg.get("timestamp"),
        }

        logger.info(f"📝 Parsed text message:\n{json.dumps(parsed_message, indent=2)}")
        return parsed_message

    except (KeyError, IndexError) as e:
        logger.warning(f"⚠️ No se pudo extraer el mensaje de texto: {e}")
        return {"status": "error", "error": str(e)}
