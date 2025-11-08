# whatsapp/webhook/route.py
import asyncio

from fastapi import APIRouter, HTTPException, Request, Response

from whatsapp.agent.agents import agent_service
from whatsapp.config import PHONE_NUMBER_ID, VERIFY_TOKEN, WHATSAPP_TOKEN, logger
from whatsapp.webhook.request.dispatcher import dispatch_message
from whatsapp.webhook.response.reply import send_text
from whatsapp.webhook.utilis.client_credentials import get_client_credentials
from whatsapp.webhook.utilis.user_verify import get_or_create_user

router = APIRouter()

# ===============================
# Helpers
# ===============================


async def parse_request_json(request: Request):
    try:
        return await request.json()
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")


def log_statuses(raw_data: dict):
    try:
        statuses = raw_data["entry"][0]["changes"][0]["value"].get("statuses", [])
        for st in statuses:
            logger.info(
                f"STATUS: {st.get('status')} | recipient={st.get('recipient_id')} | timestamp={st.get('timestamp')}"
            )
    except Exception:
        pass


async def get_business(phone_id: str):
    client = get_client_credentials(phone_id) if phone_id else None
    if client:
        logger.info(
            f"Cliente detectado: {client.get('Business Name')} | phone_id={phone_id}"
        )
    else:
        logger.warning("No se encontraron credenciales, usando .env")
    return client


async def load_instructions(role_qualifier_id: str):
    if not role_qualifier_id:
        return "Hola, soy tu asistente."
    try:
        from whatsapp.agent.load_instruction import load_instructions_from_doc

        return load_instructions_from_doc(role_qualifier_id)
    except Exception as e:
        logger.error(f"Error cargando instrucciones: {e}")
        return "Hola, soy tu asistente."


async def run_agent(message: str, role_qualifier_id: str, user_data: dict = None):
    try:
        prompt = f"Usuario: {user_data}\nMensaje: {message}" if user_data else message
        result = await agent_service(prompt, role_qualifier_id=role_qualifier_id)

        if hasattr(result, "final_output"):
            return str(result.final_output)

        if isinstance(result, dict):
            return str(result.get("final_output", result))

        return str(result)

    except Exception as e:
        logger.error(f"Error generando respuesta del agente: {e}")
        return "Lo siento, hubo un error."


async def send_whatsapp_message(
    to: str, body: str, reply_to_id: str, token: str, phone_number_id: str
):
    try:
        await send_text(
            to=to,
            body=body,
            reply_to=reply_to_id,
            token=token,
            phone_number_id=phone_number_id,
        )
    except Exception as e:
        logger.error(f"Error enviando mensaje: {e}")


def extract_whatsapp_user_info(raw_data: dict) -> dict:
    """
    Extrae información del usuario desde el payload de WhatsApp
    Retorna: {"usuario": "Fordez"} - el nombre del perfil
    """
    try:
        contacts = raw_data["entry"][0]["changes"][0]["value"].get("contacts", [])
        if contacts:
            contact = contacts[0]
            return {"usuario": contact.get("profile", {}).get("name", "")}
    except Exception as e:
        logger.error(f"Error extrayendo info de usuario: {e}")

    return {"usuario": ""}


# ===============================
# Webhook verify
# ===============================


@router.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")

    return Response(content="verify token mismatch", status_code=403)


# ===============================
# Webhook WhatsApp
# ===============================


@router.post("/webhook")
async def receive_data(request: Request):
    raw_data = await parse_request_json(request)

    logger.info("====== RAW WHATSAPP PAYLOAD ======")
    logger.info(raw_data)
    logger.info("===================================")

    log_statuses(raw_data)

    phone_id = raw_data["entry"][0]["changes"][0]["value"]["metadata"].get(
        "phone_number_id"
    )
    client = await get_business(phone_id)

    whatsapp_token = client.get("Access Token") if client else WHATSAPP_TOKEN
    phone_number_id = client.get("Phone Number ID") if client else PHONE_NUMBER_ID
    role_qualifier_id = client.get("Role Qualifier ID") if client else None
    sheet_crm_id = client.get("Sheet CRM ID") if client else None

    # Extraer info del usuario desde el payload
    user_info = extract_whatsapp_user_info(raw_data)

    transformed = dispatch_message(raw_data)
    message = transformed.get("message") or transformed.get("text")
    from_number = transformed.get("from")
    reply_to_id = transformed.get("wamid")
    canal = transformed.get("canal", "whatsapp")

    if not message:
        return {"status": "no_message"}

    # Preparar defaults con la info extraída del payload
    user_defaults = {"Usuario": user_info.get("usuario", from_number), "Canal": canal}

    user_task = get_or_create_user(from_number, sheet_crm_id, defaults=user_defaults)
    instructions_task = load_instructions(role_qualifier_id)
    user_data, instructions = await asyncio.gather(user_task, instructions_task)

    reply = await run_agent(
        message, role_qualifier_id=role_qualifier_id, user_data=user_data
    )

    await send_whatsapp_message(
        from_number, reply, reply_to_id, whatsapp_token, phone_number_id
    )

    return {"status": "ok", "user_data": user_data}


# ===============================
# Webhook Web Chat
# ===============================


@router.post("/webhook/web")
async def receive_web_data(request: Request):
    """
    Endpoint para recibir mensajes del chat web.

    Payload esperado:
    {
        "message": "Hola, necesito información",  // Texto del mensaje
        "audio": "base64_hash_audio",             // Hash del audio (opcional)
        "userName": "Juan Pérez",                 // Nombre del usuario
        "userPhone": "573001234567"               // Teléfono con código de país
    }
    """
    try:
        payload = await parse_request_json(request)

        logger.info("====== RAW WEB PAYLOAD ======")
        logger.info(payload)
        logger.info("==============================")

        # Extraer datos del payload
        message_text = payload.get("message", "")
        audio_hash = payload.get("audio")
        user_name = payload.get("userName", "")
        user_phone = payload.get("userPhone", "")

        # Validaciones
        if not user_phone:
            raise HTTPException(
                status_code=400, detail="El campo 'userPhone' es obligatorio"
            )

        if not message_text and not audio_hash:
            raise HTTPException(
                status_code=400, detail="Debe enviar 'message' o 'audio'"
            )

        logger.info(f"🌐 Mensaje web recibido de {user_name} ({user_phone})")

        # Obtener configuración del negocio (usa None para web, toma defaults de .env)
        client = await get_business(None)

        role_qualifier_id = client.get("Role Qualifier ID") if client else None
        sheet_crm_id = client.get("Sheet CRM ID") if client else None

        # Determinar el tipo de mensaje
        if message_text:
            message_type = "text"
            message_content = message_text
            logger.info(f"📝 Mensaje de texto web: {message_text}")
        else:
            message_type = "audio"
            message_content = audio_hash
            logger.info(f"🎤 Audio web recibido (hash): {audio_hash[:50]}...")

        # Preparar defaults para usuario web
        user_defaults = {"Usuario": user_phone, "Canal": "web"}

        # Cargar o crear usuario
        user_task = get_or_create_user(user_phone, sheet_crm_id, defaults=user_defaults)
        instructions_task = load_instructions(role_qualifier_id)
        user_data, instructions = await asyncio.gather(user_task, instructions_task)

        # Procesar según el tipo de mensaje
        if message_type == "text":
            # Procesar mensaje de texto con el agente
            reply = await run_agent(
                message_text, role_qualifier_id=role_qualifier_id, user_data=user_data
            )
        else:
            # Si es audio, indicar que se procesará
            # Aquí puedes agregar lógica para procesar el audio
            # Por ejemplo: await process_audio(audio_hash, user_phone, sheet_crm_id)
            reply = "Hemos recibido tu mensaje de audio y lo estamos procesando. Te responderemos pronto."
            logger.info(
                f"🎤 Audio recibido de {user_phone}, pendiente de transcripción"
            )

        return {
            "status": "ok",
            "reply": reply,
            "user_data": user_data,
            "message_type": message_type,
            "audio_pending": message_type == "audio",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error procesando mensaje web: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
