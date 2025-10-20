from fastapi import APIRouter, Request, Header, HTTPException, Response
from whatsapp.agent.agents import marketing_agent
from whatsapp.webhook.security import verify_signature
from whatsapp.webhook.request.dispatcher import dispatch_message
from whatsapp.webhook.response.reply import send_text
from config import VERIFY_TOKEN, logger

router = APIRouter()

# Diccionario para mantener la memoria por usuario
user_histories = {}

chat = marketing_agent  # agente único


@router.get("/webhook")
async def verify(request: Request):
    """
    Endpoint de verificación de WhatsApp.
    Devuelve el 'hub.challenge' en texto plano si el token coincide.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ WEBHOOK_VERIFIED")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("❌ Verify token mismatch")
    return Response(content="verify token mismatch", status_code=403)


@router.post("/webhook")
async def receive_data(request: Request, x_hub_signature_256: str = Header(None)):
    """
    Recibe mensajes de WhatsApp, valida firma, los procesa con el agente y responde.
    Mantiene memoria completa por usuario.
    """
    body = await request.body()

    if not x_hub_signature_256:
        raise HTTPException(status_code=400, detail="Missing signature header")

    # Validar firma
    try:
        verify_signature(body, x_hub_signature_256)
    except Exception as e:
        logger.error(f"❌ Invalid signature: {e}")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parsear JSON
    try:
        raw_data = await request.json()
    except Exception as e:
        logger.error(f"❌ Error parsing JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Transformar data
    transformed_data = dispatch_message(raw_data)
    message = transformed_data.get("message") or transformed_data.get("text")
    from_number = transformed_data.get("from")
    reply_to_id = transformed_data.get("wamid")

    if not message:
        logger.info("⚠️ No se encontró texto en el mensaje")
        return {"status": "no_message"}

    logger.info(f"📝 Parsed text message from {from_number}: {message}")

    # Inicializar historial del usuario si no existe
    if from_number not in user_histories:
        user_histories[from_number] = []

    # Guardar mensaje del usuario
    user_histories[from_number].append({"role": "user", "content": message})

    # Generar respuesta usando todo el historial del usuario
    try:
        reply = chat.generate_reply(
            messages=[{"role": "system", "content": chat.system_message}]
            + user_histories[from_number]
        )
        logger.info(f"💬 Agent reply: {reply}")
        # Guardar respuesta del agente
        user_histories[from_number].append({"role": "assistant", "content": reply})
    except Exception as e:
        logger.error(f"❌ Error generando respuesta del agente: {e}")
        reply = "Lo siento, hubo un error procesando tu mensaje."

    # Enviar la respuesta a WhatsApp
    try:
        await send_text(to=from_number, body=reply, reply_to=reply_to_id)
        logger.info(f"✅ Mensaje enviado a {from_number}")
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje: {e}")

    return {"status": "ok"}
