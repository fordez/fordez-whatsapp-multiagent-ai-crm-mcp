import asyncio
import logging
import re

import httpx
import openai
from fastapi import APIRouter, HTTPException, Request, Response

from whatsapp.agent.agents import agent_service
from whatsapp.agent.load_instruction import load_instructions_for_user
from whatsapp.config import config
from whatsapp.webhook.request.dispatcher import dispatch_message
from whatsapp.webhook.response.reply import send_text
from whatsapp.webhook.response.typing import send_typing_indicator
from whatsapp.webhook.utilis.client_credentials import get_client_credentials
from whatsapp.webhook.utilis.user_verify import get_or_create_user

logger = logging.getLogger("whatsapp")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

router = APIRouter()


# ==========================================================
# Helpers
# ==========================================================
async def parse_request_json(request: Request):
    try:
        return await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")


def safe_get(d: dict, key: str, default=None):
    return d.get(key) if d and key in d else default


async def get_business(phone_id: str):
    client = get_client_credentials(phone_id) if phone_id else None
    return client


async def send_whatsapp_message(
    to: str, body: str, reply_to_id: str, token: str, phone_number_id: str
):
    try:
        if not (to and body and token and phone_number_id):
            logger.info(f"Mensaje a {to}: Entrega fallida (datos incompletos)")
            return
        await send_text(
            to=to,
            body=body,
            reply_to=reply_to_id,
            token=token,
            phone_number_id=phone_number_id,
        )
        logger.info(f"Mensaje a {to}: Entrega exitosa")
    except Exception as e:
        logger.info(f"Mensaje a {to}: Entrega fallida (Error: {str(e)})")


def extract_whatsapp_user_info(raw_data: dict) -> dict:
    contacts = (
        raw_data.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("contacts", [])
    )
    if contacts:
        contact = contacts[0]
        return {"usuario": contact.get("profile", {}).get("name", "")}
    return {"usuario": ""}


def get_media_url(media_id: str, token: str):
    url = f"https://graph.facebook.com/v20.0/{media_id}"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json().get("url")


def download_media(media_url: str, token: str):
    resp = httpx.get(media_url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.content


def transcribe_audio(audio_bytes: bytes):
    resp = openai.audio.transcriptions.create(
        model="gpt-4o-transcribe", file=("audio.ogg", audio_bytes)
    )
    return resp.text


# ==========================================================
# Normalizar números argentinos
# ==========================================================
def normalize_whatsapp_number(phone: str) -> str:
    """
    Normaliza números para WhatsApp Cloud API.

    - Argentina (+54):
        - Elimina el '15' después del código de área.
        - Agrega un '9' después del código de país si falta.
        - Resultado: +54 9 [código de área] [número]
    - Otros países: solo elimina espacios, guiones y paréntesis.

    Args:
        phone (str): Número de teléfono recibido del webhook.

    Returns:
        str: Número en formato internacional válido.
    """
    if not phone:
        return phone

    original_phone = phone
    phone = re.sub(r"[^\d+]", "", phone)

    if phone.startswith("+54"):
        match = re.match(r"(\+54)(\d{2,4})(15)?(\d+)", phone)
        if match:
            plus54, area, _, number = match.groups()
            phone = f"{plus54}9{area}{number}"
        else:
            if not phone.startswith("+549"):
                phone = phone.replace("+54", "+549", 1)

    logger.info(f"Normalized phone: {original_phone} -> {phone}")
    return phone


# ==========================================================
# WEBHOOK VERIFY
# ==========================================================
@router.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == config.verify_token:
        return Response(content=challenge, media_type="text/plain")

    return Response(content="verify token mismatch", status_code=403)


# ==========================================================
# WEBHOOK WHATSAPP
# ==========================================================
@router.post("/webhook")
async def receive_data(request: Request):
    raw_data = await parse_request_json(request)

    phone_id = (
        raw_data.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("metadata", {})
        .get("phone_number_id")
    )
    client = await get_business(phone_id)

    whatsapp_token = safe_get(client, "Access Token")
    phone_number_id = safe_get(client, "Phone Number ID")
    sheet_crm_id = safe_get(client, "Sheet CRM ID")
    role_id = safe_get(client, "Role ID")

    if not (whatsapp_token and phone_number_id and role_id):
        logger.info(f"Mensaje a {phone_id}: Credenciales incompletas")
        return {"status": "error", "message": "Credenciales incompletas"}

    transformed = dispatch_message(raw_data)
    if not transformed:
        return {"status": "no_message"}

    message = transformed.get("message") or transformed.get("text")
    from_number = transformed.get("from")
    reply_to_id = transformed.get("wamid")

    # ✅ Normalizar número argentino correctamente
    from_number = normalize_whatsapp_number(from_number)

    if reply_to_id:
        asyncio.create_task(
            send_typing_indicator(
                message_id=reply_to_id,
                token=whatsapp_token,
                phone_number_id=phone_number_id,
            )
        )

    user_info = extract_whatsapp_user_info(raw_data)

    media_id = transformed.get("media_id")
    msg_type = transformed.get("type")
    if msg_type == "audio" and media_id:
        try:
            media_url = get_media_url(media_id, whatsapp_token)
            audio_bytes = download_media(media_url, whatsapp_token)
            transcript = transcribe_audio(audio_bytes)
            message = transcript
        except Exception:
            message = "No pude procesar tu audio."

    if not message:
        return {"status": "no_message"}

    user_defaults = {
        "Usuario": user_info.get("usuario", from_number),
        "Canal": "whatsapp",
    }
    user_data = await get_or_create_user(
        from_number, sheet_crm_id, defaults=user_defaults
    )
    if not user_data:
        user_data = {}

    instructions = await load_instructions_for_user(role_id, client)
    session_key = from_number

    reply_dict = await agent_service(
        user_message=message,
        system_instructions=instructions,
        session_key=session_key,
        user_data=user_data,
        sheet_crm_id=sheet_crm_id,
    )

    reply = reply_dict.get("final_output", "No pude generar respuesta.")

    await send_whatsapp_message(
        to=from_number,
        body=reply,
        reply_to_id=reply_to_id,
        token=whatsapp_token,
        phone_number_id=phone_number_id,
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
