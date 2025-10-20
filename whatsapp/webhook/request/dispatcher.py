from whatsapp.webhook.request.handlers.text import handle_text
from whatsapp.webhook.request.handlers.image import handle_image
from whatsapp.webhook.request.handlers.audio import handle_audio
from whatsapp.webhook.request.handlers.video import handle_video
from whatsapp.webhook.request.handlers.document import handle_document
from whatsapp.webhook.request.handlers.location import handle_location
from whatsapp.webhook.request.handlers.contact import handle_contact
from whatsapp.webhook.request.handlers.reaction import handle_reaction


def dispatch_message(raw_data):
    """
    Recibe todo el raw_data del webhook y llama al handler correspondiente
    según el tipo de mensaje detectado dentro del handler.
    """

    # Tomamos solo el primer mensaje para simplificar
    try:
        msg = raw_data["entry"][0]["changes"][0]["value"]["messages"][0]
    except (KeyError, IndexError):
        print("⚠️ No se encontró ningún mensaje en el webhook")
        return {"status": "no_message"}

    msg_type = msg.get("type")
    if not msg_type:
        print("⚠️ Mensaje sin tipo definido")
        return {"status": "unknown_type"}

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

    handler = handlers.get(msg_type)
    if handler:
        # Pasamos todo raw_data al handler, que se encargará de extraer todo
        return handler(raw_data)
    else:
        print(f"⚠️ Tipo de mensaje no soportado: {msg_type}")
        return {"status": "unsupported", "type": msg_type}
