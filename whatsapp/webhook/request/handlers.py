"""
Todos los handlers de WhatsApp unificados en un solo archivo.
Cada handler recibe:
    - msg: mensaje ya identificado
    - raw_data: payload completo original

Extrae información del payload:
    - canal: siempre "whatsapp"
    - usuario: wa_id del contacto
    - nombre: nombre del perfil del contacto
"""


def extract_user_info(raw_data: dict) -> dict:
    """
    Extrae información del usuario desde el payload de WhatsApp.
    Retorna: {"usuario": "573146964611", "nombre": "Fordez"}
    """
    try:
        contacts = raw_data["entry"][0]["changes"][0]["value"].get("contacts", [])
        if contacts:
            contact = contacts[0]
            return {
                "usuario": contact.get("wa_id", ""),
                "nombre": contact.get("profile", {}).get("name", ""),
            }
    except Exception:
        pass

    return {"usuario": "", "nombre": ""}


def handle_text(msg, raw_data):
    user_info = extract_user_info(raw_data)
    return {
        "type": "text",
        "message": msg.get("text", {}).get("body", ""),
        "from": msg.get("from"),
        "wamid": msg.get("id"),
        "canal": "whatsapp",
        "usuario": user_info.get("usuario"),
        "nombre": user_info.get("nombre"),
        "raw": raw_data,
    }


def handle_image(msg, raw_data):
    user_info = extract_user_info(raw_data)
    img = msg.get("image", {})
    return {
        "type": "image",
        "media_id": img.get("id"),
        "caption": img.get("caption"),
        "from": msg.get("from"),
        "wamid": msg.get("id"),
        "canal": "whatsapp",
        "usuario": user_info.get("usuario"),
        "nombre": user_info.get("nombre"),
        "raw": raw_data,
    }


def handle_audio(msg, raw_data):
    user_info = extract_user_info(raw_data)
    audio = msg.get("audio", {})
    return {
        "type": "audio",
        "media_id": audio.get("id"),
        "mime_type": audio.get("mime_type"),
        "from": msg.get("from"),
        "wamid": msg.get("id"),
        "canal": "whatsapp",
        "usuario": user_info.get("usuario"),
        "nombre": user_info.get("nombre"),
        "raw": raw_data,
    }


def handle_video(msg, raw_data):
    user_info = extract_user_info(raw_data)
    video = msg.get("video", {})
    return {
        "type": "video",
        "media_id": video.get("id"),
        "caption": video.get("caption"),
        "from": msg.get("from"),
        "wamid": msg.get("id"),
        "canal": "whatsapp",
        "usuario": user_info.get("usuario"),
        "nombre": user_info.get("nombre"),
        "raw": raw_data,
    }


def handle_document(msg, raw_data):
    user_info = extract_user_info(raw_data)
    doc = msg.get("document", {})
    return {
        "type": "document",
        "media_id": doc.get("id"),
        "filename": doc.get("filename"),
        "mime_type": doc.get("mime_type"),
        "from": msg.get("from"),
        "wamid": msg.get("id"),
        "canal": "whatsapp",
        "usuario": user_info.get("usuario"),
        "nombre": user_info.get("nombre"),
        "raw": raw_data,
    }


def handle_location(msg, raw_data):
    user_info = extract_user_info(raw_data)
    loc = msg.get("location", {})
    return {
        "type": "location",
        "lat": loc.get("latitude"),
        "lng": loc.get("longitude"),
        "name": loc.get("name"),
        "address": loc.get("address"),
        "from": msg.get("from"),
        "wamid": msg.get("id"),
        "canal": "whatsapp",
        "usuario": user_info.get("usuario"),
        "nombre": user_info.get("nombre"),
        "raw": raw_data,
    }


def handle_contact(msg, raw_data):
    user_info = extract_user_info(raw_data)
    return {
        "type": "contacts",
        "contacts": msg.get("contacts", []),
        "from": msg.get("from"),
        "wamid": msg.get("id"),
        "canal": "whatsapp",
        "usuario": user_info.get("usuario"),
        "nombre": user_info.get("nombre"),
        "raw": raw_data,
    }


def handle_reaction(msg, raw_data):
    user_info = extract_user_info(raw_data)
    reaction = msg.get("reaction", {})
    return {
        "type": "reaction",
        "emoji": reaction.get("emoji"),
        "msg_id": reaction.get("message_id"),
        "from": msg.get("from"),
        "wamid": msg.get("id"),
        "canal": "whatsapp",
        "usuario": user_info.get("usuario"),
        "nombre": user_info.get("nombre"),
        "raw": raw_data,
    }


def handle_unknown(msg, raw_data):
    user_info = extract_user_info(raw_data)
    return {
        "type": "unknown",
        "from": msg.get("from"),
        "wamid": msg.get("id"),
        "canal": "whatsapp",
        "usuario": user_info.get("usuario"),
        "nombre": user_info.get("nombre"),
        "raw": raw_data,
    }
