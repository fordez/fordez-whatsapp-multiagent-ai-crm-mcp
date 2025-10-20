import json
from config import logger

def handle_audio(raw_msg: dict):
    """
    Handle incoming WhatsApp audio messages.
    Parses the raw payload inline and prints the simplified object.
    """
    try:
        entry = raw_msg["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        msg = value["messages"][0]
        audio = msg.get("audio", {})

        # Para audio no hay caption -> mensaje genérico
        message = f"{msg.get('type')} - {audio.get('mime_type')}"

        parsed_data = {
            # Common info
            "account_id": entry.get("id"),
            "channel": "whatsapp",
            "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
            "contacts_name": value.get("contacts", [{}])[0].get("profile", {}).get("name"),
            "contacts_phone_number": value.get("contacts", [{}])[0].get("wa_id"),
            "message_id": msg.get("id"),
            "type": msg.get("type"),  # será 'audio'
            "timestamp": msg.get("timestamp"),
            # Media info
            "filename": audio.get("filename"),   # normalmente None
            "message": message,                  # no hay caption, solo fallback
            "audio_id": audio.get("id"),
            "mime_type": audio.get("mime_type"),
            "sha256": audio.get("sha256"),
            "voice": audio.get("voice"),         # True si es nota de voz
        }

        logger.info(f"🎵 Parsed audio message:\n{json.dumps(parsed_data, indent=2)}")

    except Exception as e:
        logger.warning(f"⚠️ Could not parse audio message: {e}")
