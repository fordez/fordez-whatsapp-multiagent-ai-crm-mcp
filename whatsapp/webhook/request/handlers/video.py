import json
from config import logger

def handle_video(raw_msg: dict):
    """
    Handle incoming WhatsApp video messages.
    Parses the raw payload inline and prints the simplified object.
    """
    try:
        entry = raw_msg["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        msg = value["messages"][0]
        video = msg.get("video", {})

        # message = caption si existe, si no = "type - mime_type"
        message = video.get("caption") or f"{msg.get('type')} - {video.get('mime_type')}"

        parsed_data = {
            # Common info
            "account_id": entry.get("id"),
            "channel": "whatsapp",
            "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
            "contacts_name": value.get("contacts", [{}])[0].get("profile", {}).get("name"),
            "contacts_phone_number": value.get("contacts", [{}])[0].get("wa_id"),
            "message_id": msg.get("id"),
            "type": msg.get("type"),  # será 'video'
            "timestamp": msg.get("timestamp"),
            # Media info
            "filename": video.get("filename"),  # normalmente None en video
            "message": message,                 # caption o fallback
            "video_id": video.get("id"),
            "mime_type": video.get("mime_type"),
            "sha256": video.get("sha256"),
        }

        logger.info(f"🎥 Parsed video message:\n{json.dumps(parsed_data, indent=2)}")

    except Exception as e:
        logger.warning(f"⚠️ Could not parse video message: {e}")
