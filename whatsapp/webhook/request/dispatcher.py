"""
Dispatcher único para WhatsApp.
Solo decide qué handler usar y devuelve un mensaje unificado.
"""

from whatsapp.webhook.request.handlers import (
    handle_audio,
    handle_contact,
    handle_document,
    handle_image,
    handle_location,
    handle_reaction,
    handle_text,
    handle_unknown,
    handle_video,
)


def dispatch_message(raw_data):
    """
    Toma todo el raw_data del webhook.
    Extrae el primer mensaje y llama al handler según msg['type'].
    """

    # ✅ Extraer el mensaje principal de forma segura
    try:
        entry = raw_data["entry"][0]["changes"][0]["value"]
        messages = entry.get("messages", [])
        if not messages:
            return {"status": "no_message", "raw": raw_data}

        msg = messages[0]
    except Exception:
        return {"status": "invalid_payload", "raw": raw_data}

    msg_type = msg.get("type")

    # ✅ Tabla centralizada de handlers
    handlers = {
        "text": handle_text,
        "image": handle_image,
        "audio": handle_audio,
        "video": handle_video,
        "document": handle_document,
        "location": handle_location,
        "contacts": handle_contact,
        "reaction": handle_reaction,
    }

    # ✅ Seleccionar handler o fallback
    handler = handlers.get(msg_type, handle_unknown)

    # ✅ Ejecutar handler con mensaje + raw original
    return handler(msg, raw_data)
