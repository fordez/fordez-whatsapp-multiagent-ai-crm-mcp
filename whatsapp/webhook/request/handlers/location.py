import json
from config import logger

def handle_location(raw_msg: dict):
    """
    Handle incoming WhatsApp location messages.
    Parses the raw payload inline and prints the simplified object.
    """
    try:
        entry = raw_msg["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        msg = value["messages"][0]
        location = msg.get("location", {})

        parsed_data = {
            # Common info
            "account_id": entry.get("id"),
            "channel": "whatsapp",
            "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
            "contacts_name": value.get("contacts", [{}])[0].get("profile", {}).get("name"),
            "contacts_phone_number": value.get("contacts", [{}])[0].get("wa_id"),
            "message_id": msg.get("id"),
            "type": msg.get("type"),   # 'location'
            "timestamp": msg.get("timestamp"),
            # Location info
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "message": f"Shared location (latitude: {location.get('latitude')}, longitude: {location.get('longitude')})"
        }

        logger.info(f"📍 Parsed location message:\n{json.dumps(parsed_data, indent=2)}")

    except Exception as e:
        logger.warning(f"⚠️ Could not parse location message: {e}")
