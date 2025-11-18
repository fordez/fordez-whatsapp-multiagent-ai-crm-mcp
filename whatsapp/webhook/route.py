# ==========================================================
# whatsapp/webhook/route.py - WEBHOOK WEB CON PHONE_ID EN URL
# Combinación Opción 2 + 3: Reutiliza la lógica existente
# CON VALIDACIÓN DE STATUS
# ==========================================================

import asyncio
import json
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
from whatsapp.webhook.response.web_reply import (
    send_web_message,
    send_web_typing_indicator,
)
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
# Helpers (mantienen igual)
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
        logger.info(f"🔍 === ENVIANDO MENSAJE ===")
        logger.info(f"   Destinatario: '{to}' (len={len(to)})")
        logger.info(f"   Phone Number ID: {phone_number_id}")
        logger.info(f"   Mensaje: {body[:50]}...")
        logger.info(f"   Reply to ID: {reply_to_id}")

        if not (to and body and token and phone_number_id):
            logger.error(f"❌ Mensaje a {to}: Entrega fallida (datos incompletos)")
            logger.error(
                f"   to={bool(to)}, body={bool(body)}, token={bool(token)}, phone_id={bool(phone_number_id)}"
            )
            return

        await send_text(
            to=to,
            body=body,
            reply_to=reply_to_id,
            token=token,
            phone_number_id=phone_number_id,
        )
        logger.info(f"✅ Mensaje a {to}: Entrega exitosa")

    except Exception as e:
        logger.error(f"❌ Mensaje a {to}: Entrega fallida")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Tipo: {type(e).__name__}")


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


def normalize_whatsapp_number(raw: str) -> str:
    """
    Normaliza números argentinos EXACTAMENTE como necesita Meta:

    Si llega: 5493412732652
    Debe devolver: 54341152732652

    - Remueve el 9 después del prefijo 54
    - Respeta código de área de 3 dígitos (ej: 341)
    - Inserta 15 ANTES del número local
    """

    if not raw:
        return raw

    # Mantener solo números
    n = "".join(c for c in raw if c.isdigit())

    # Si NO es Argentina → devolver igual
    if not n.startswith("54"):
        return n

    # Remover prefijo país
    resto = n[2:]  # Ej: 93412732652

    # Si el primer dígito es 9 → removerlo (regla Argentina)
    if resto.startswith("9"):
        resto = resto[1:]  # → 3412732652

    # Código de área argentino típico: 3 dígitos
    codigo_area = resto[:3]  # 341
    numero_local = resto[3:]  # 2732652

    # Insertar 15 ANTES del número local
    return f"54{codigo_area}15{numero_local}"


# ==========================================================
# ✅ NUEVA FUNCIÓN: VALIDAR STATUS DEL NEGOCIO
# ==========================================================
def validate_business_status(client: dict, phone_id: str) -> bool:
    """
    Valida que el negocio tenga Status = TRUE

    Args:
        client: Diccionario con los datos del negocio
        phone_id: ID del teléfono para logging

    Returns:
        True si el status es True, False en caso contrario
    """
    if not client:
        logger.error(f"❌ Phone ID {phone_id}: Cliente no encontrado")
        return False

    status = safe_get(client, "Status")
    business_name = safe_get(client, "Business Name", "Desconocido")

    # Convertir a booleano si viene como string
    if isinstance(status, str):
        status = status.lower() in ("true", "1", "yes", "si", "sí")

    if not status:
        logger.warning(
            f"⛔ Negocio '{business_name}' (Phone ID: {phone_id}): Status = FALSE - Agente desactivado"
        )
        return False

    logger.info(
        f"✅ Negocio '{business_name}' (Phone ID: {phone_id}): Status = TRUE - Agente activo"
    )
    return True


# ==========================================================
# WEBHOOK VERIFY (WhatsApp)
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
# ✅ NUEVA FUNCIÓN: FILTRAR NOTIFICACIONES DE ESTADO
# ==========================================================
def should_process_webhook(raw_data: dict) -> bool:
    """
    Determina si el webhook debe procesarse o ignorarse.

    Ignora:
    - Notificaciones de estado (sent, delivered, read, failed)
    - Mensajes enviados por el negocio
    - Webhooks sin mensajes

    Args:
        raw_data: Payload completo del webhook

    Returns:
        True si debe procesarse, False si debe ignorarse
    """
    try:
        entry = raw_data.get("entry", [])
        if not entry:
            logger.info("⏭️ Webhook ignorado: No hay entry")
            return False

        changes = entry[0].get("changes", [])
        if not changes:
            logger.info("⏭️ Webhook ignorado: No hay changes")
            return False

        value = changes[0].get("value", {})

        # 1. Verificar si es una notificación de estado
        statuses = value.get("statuses", [])
        if statuses:
            status_info = statuses[0]
            status_type = status_info.get("status", "unknown")
            recipient = status_info.get("recipient_id", "unknown")
            logger.info(
                f"⏭️ Notificación de estado ignorada: {status_type} para {recipient}"
            )
            return False

        # 2. Verificar si hay mensajes
        messages = value.get("messages", [])
        if not messages:
            logger.info("⏭️ Webhook ignorado: No hay messages")
            return False

        # 3. Verificar que el mensaje sea del usuario (no del negocio)
        message = messages[0]
        message_from = message.get("from", "")

        # Si el mensaje tiene el campo "from", es del usuario
        # Los mensajes del negocio no tienen este campo o tienen estructura diferente
        if not message_from:
            logger.info("⏭️ Webhook ignorado: Mensaje sin remitente válido")
            return False

        # 4. Verificar tipos de mensaje válidos
        message_type = message.get("type", "")
        valid_types = [
            "text",
            "audio",
            "image",
            "video",
            "document",
            "button",
            "interactive",
        ]

        if message_type not in valid_types:
            logger.info(
                f"⏭️ Webhook ignorado: Tipo de mensaje no válido: {message_type}"
            )
            return False

        logger.info(
            f"✅ Webhook válido: Mensaje tipo '{message_type}' de {message_from}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Error al validar webhook: {e}")
        return False


# ==========================================================
# WEBHOOK WHATSAPP
# ==========================================================
@router.post("/webhook")
async def receive_data(request: Request):
    raw_data = await parse_request_json(request)

    # ✅ FILTRAR NOTIFICACIONES DE ESTADO PRIMERO
    if not should_process_webhook(raw_data):
        return {"status": "ignored", "reason": "notification or invalid message"}

    phone_id = (
        raw_data.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("metadata", {})
        .get("phone_number_id")
    )
    client = await get_business(phone_id)

    # ✅ VALIDAR STATUS ANTES DE CONTINUAR
    if not validate_business_status(client, phone_id):
        logger.warning(
            f"⛔ Mensaje ignorado - Negocio desactivado (Phone ID: {phone_id})"
        )
        return {
            "status": "disabled",
            "message": "El agente está desactivado para este negocio",
        }

    whatsapp_token = safe_get(client, "Access Token")
    phone_number_id = safe_get(client, "Phone Number ID")
    sheet_crm_id = safe_get(client, "Sheet CRM ID")
    role_id = safe_get(client, "Role ID")

    if not (whatsapp_token and phone_number_id and role_id):
        logger.error(f"❌ Mensaje a {phone_id}: Credenciales incompletas")
        logger.error(
            f"   token={bool(whatsapp_token)}, phone_id={bool(phone_number_id)}, role={bool(role_id)}"
        )
        return {"status": "error", "message": "Credenciales incompletas"}

    transformed = dispatch_message(raw_data)
    if not transformed:
        return {"status": "no_message"}

    message = transformed.get("message") or transformed.get("text")
    from_number = transformed.get("from")
    reply_to_id = transformed.get("wamid")

    logger.info(f"📥 Número original recibido: {from_number}")

    # Normalización
    from_number = normalize_whatsapp_number(from_number)

    logger.info(f"📥 Número normalizado: {from_number}")

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
        except Exception as e:
            logger.error(f"❌ Error procesando audio: {e}")
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

    logger.info(f"🤖 Procesando mensaje de {from_number}: {message[:50]}...")

    reply_dict = await agent_service(
        user_message=message,
        system_instructions=instructions,
        session_key=session_key,
        user_data=user_data,
        sheet_crm_id=sheet_crm_id,
    )

    reply = reply_dict.get("final_output", "No pude generar respuesta.")

    logger.info(f"💬 Respuesta generada para {from_number}: {reply[:50]}...")

    await send_whatsapp_message(
        to=from_number,
        body=reply,
        reply_to_id=reply_to_id,
        token=whatsapp_token,
        phone_number_id=phone_number_id,
    )

    return {"status": "ok", "user_data": user_data}


# ==========================================================
# WEBHOOK WEB - CON PHONE_ID EN LA URL
# ==========================================================
@router.post("/webhook/web/{phone_number_id}")
async def receive_web_data(request: Request, phone_number_id: str):
    try:
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8", errors="ignore")

        logger.info(
            f"\n===== 🌐 WEBHOOK-WEB RECIBIDO (Phone ID: {phone_number_id}) ====="
        )

        try:
            payload = json.loads(body_str)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON inválido: {e}")
            raise HTTPException(status_code=400, detail=f"JSON inválido: {str(e)}")

        logger.info(json.dumps(payload, indent=2, ensure_ascii=False))
        logger.info("===== 🌐 FIN WEBHOOK-WEB ============\n")

        user_phone = payload.get("userPhone") or payload.get("session_id")
        message = payload.get("message") or payload.get("text")
        user_name = payload.get("user_name") or payload.get("userName", "Usuario Web")
        webhook_response_url = payload.get("webhook_url") or payload.get("webhookUrl")

        session_id = user_phone

        logger.info(
            f"📥 Datos: session_id={session_id}, phone_id={phone_number_id}, user={user_name}"
        )

        if not session_id:
            logger.error("❌ Falta userPhone o session_id")
            return {"status": "error", "message": "Falta userPhone o session_id"}

        if not message:
            logger.error("❌ Falta message")
            return {"status": "error", "message": "Falta message"}

        logger.info(f"🔍 Buscando negocio con Phone ID: {phone_number_id}")
        client = await get_business(phone_number_id)

        if not client:
            logger.error(f"❌ Phone ID {phone_number_id} no encontrado")
            return {
                "status": "error",
                "message": f"Phone ID {phone_number_id} no encontrado",
            }

        # ✅ VALIDAR STATUS ANTES DE CONTINUAR
        if not validate_business_status(client, phone_number_id):
            logger.warning(
                f"⛔ Mensaje web ignorado - Negocio desactivado (Phone ID: {phone_number_id})"
            )

            # Opcionalmente, enviar mensaje al usuario informando que el servicio está desactivado
            if webhook_response_url:
                await send_web_message(
                    session_id=session_id,
                    message="Lo sentimos, el servicio está temporalmente desactivado. Por favor, intenta más tarde.",
                    webhook_url=webhook_response_url,
                    metadata={"status": "disabled"},
                )

            return {
                "status": "disabled",
                "message": "El agente está desactivado para este negocio",
                "phone_number_id": phone_number_id,
            }

        sheet_crm_id = safe_get(client, "Sheet CRM ID")
        role_id = safe_get(client, "Role ID")
        business_name = safe_get(client, "Business Name", "Negocio Web")

        logger.info(f"✅ Negocio encontrado: {business_name}")
        logger.info(f"   - Sheet CRM ID: {sheet_crm_id}")
        logger.info(f"   - Role ID: {role_id}")

        if not role_id:
            logger.error(f"❌ Negocio {business_name}: Falta role_id")
            return {
                "status": "error",
                "message": "Configuración incompleta: falta role_id",
            }

        if webhook_response_url:
            logger.info(f"⌨️ Enviando typing indicator a: {webhook_response_url}")
            asyncio.create_task(
                send_web_typing_indicator(
                    session_id=session_id, webhook_url=webhook_response_url
                )
            )

        user_defaults = {
            "Nombre": user_name,
            "Usuario": user_name,
            "Canal": "web",
            "Negocio": business_name,
        }

        logger.info(
            f"👤 Obteniendo/creando usuario: {session_id} (Nombre: {user_name})"
        )
        user_data = await get_or_create_user(
            session_id, sheet_crm_id, defaults=user_defaults
        )
        if not user_data:
            user_data = {}
            logger.warning(f"⚠️ Usuario {session_id}: No se pudo crear/obtener datos")
        else:
            logger.info(
                f"✅ Usuario obtenido/creado: {user_data.get('Usuario', 'Sin nombre')}"
            )

        logger.info(f"📋 Cargando instrucciones para role_id: {role_id}")
        instructions = await load_instructions_for_user(role_id, client)

        logger.info(f"🤖 Procesando mensaje con agent_service...")
        reply_dict = await agent_service(
            user_message=message,
            system_instructions=instructions,
            session_key=session_id,
            user_data=user_data,
            sheet_crm_id=sheet_crm_id,
        )

        reply = reply_dict.get("final_output", "No pude generar respuesta.")
        logger.info(f"💬 Respuesta generada: {reply[:100]}...")

        success = False
        if webhook_response_url:
            logger.info(f"📤 Enviando respuesta a: {webhook_response_url}")
            success = await send_web_message(
                session_id=session_id,
                message=reply,
                webhook_url=webhook_response_url,
                metadata={
                    "timestamp": payload.get("timestamp"),
                    "user_name": user_name,
                    "business_name": business_name,
                    "phone_number_id": phone_number_id,
                },
            )

            if success:
                logger.info(
                    f"✅ Respuesta web enviada exitosamente a sesión: {session_id}"
                )
            else:
                logger.error(f"❌ Error enviando respuesta web a: {session_id}")
        else:
            logger.info(f"📋 Respuesta generada (sin webhook): {reply[:100]}...")
            success = True

        return {
            "status": "ok",
            "session_id": session_id,
            "phone_number_id": phone_number_id,
            "business_name": business_name,
            "user_data": user_data,
            "message_sent": success,
            "reply": reply,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error procesando mensaje web: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
