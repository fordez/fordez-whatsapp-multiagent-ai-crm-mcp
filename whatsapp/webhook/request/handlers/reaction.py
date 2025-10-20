import json
from config import logger

def handle_reaction(raw_msg: dict):
    """
    Handle incoming WhatsApp reaction messages.
    Parses the raw payload inline and prints the simplified object.
    """
    try:
        entry = raw_msg["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        msg = value["messages"][0]
        reaction = msg.get("reaction", {})

        parsed_data = {
            # Common info
            "account_id": entry.get("id"),
            "channel": "whatsapp",
            "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
            "contacts_name": value.get("contacts", [{}])[0].get("profile", {}).get("name"),
            "contacts_phone_number": value.get("contacts", [{}])[0].get("wa_id"),
            "message_id": msg.get("id"),
            "type": msg.get("type"),   # 'reaction'
            "timestamp": msg.get("timestamp"),
            # Reaction info
            "emoji": reaction.get("emoji"),
            "reaction_to_message_id": reaction.get("message_id"),
            "message": f"Reaction {reaction.get('emoji')} al mensaje {reaction.get('message_id')}"
        }

        logger.info(f"😀 Parsed reaction message:\n{json.dumps(parsed_data, indent=2)}")

    except Exception as e:
        logger.warning(f"⚠️ Could not parse reaction message: {e}")
