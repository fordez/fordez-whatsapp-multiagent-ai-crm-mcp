import json
from config import logger


def handle_contact(raw_msg: dict):
    """Parse WhatsApp contact message"""
    try:
        entry = raw_msg["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        msg = value["messages"][0]
        contact = msg.get("contacts", [{}])[0]

        name = contact.get("name", {}).get("formatted_name")
        phone = contact.get("phones", [{}])[0].get("phone")

        parsed_data = {
            "account_id": entry.get("id"),
            "channel": "whatsapp",
            "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
            "contacts_name": value.get("contacts", [{}])[0].get("profile", {}).get("name"),
            "contacts_phone_number": value.get("contacts", [{}])[0].get("wa_id"),
            "message_id": msg.get("id"),
            "type": msg.get("type"),
            "timestamp": msg.get("timestamp"),
            "message": f"Contact shared: {name} ({phone})",
            "contact_name": name,
            "contact_phone": phone,
        }
        logger.info(f"👤 Parsed contact:\n{json.dumps(parsed_data, indent=2)}")
    except Exception as e:
        logger.warning(f"⚠️ Could not parse contact: {e}")
