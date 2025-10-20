from fastapi import APIRouter, Request, Header, HTTPException
from whatsapp.agent.chat import MarketingChat
from whatsapp.webhook.security import verify_signature
from whatsapp.webhook.request.dispatcher import dispatch_message
from whatsapp.webhook.response.reply import send_text  # 👈 tu módulo de envío
from config import VERIFY_TOKEN, logger

router = APIRouter()
chat = MarketingChat()  # Mantener estado del chat


@router.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ WEBHOOK_VERIFIED")
        return challenge
    return "❌ verify token mismatch"


@router.post("/webhook")
async def receive_data(request: Request, x_hub_signature_256: str = Header(None)):
    body = await request.body()

    if not x_hub_signature_256:
        raise HTTPException(status_code=400, detail="Missing signature header")

    # Validar firma
    verify_signature(body, x_hub_signature_256)

    # Parsear JSON
    try:
        raw_data = await request.json()
    except Exception as e:
        logger.error(f"❌ Error parsing JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Transformar data
    transformed_data = dispatch_message(raw_data)
    message = transformed_data.get("message") or transformed_data.get("text")
    from_number = transformed_data.get("from")  # número del usuario
    reply_to_id = transformed_data.get("wamid")  # id de mensaje original para contexto

    if message:
        logger.info(f"📝 Parsed text message: {message}")
    else:
        logger.info("⚠️ No se encontró texto en el mensaje")
        return {"status": "no_message"}

    # Routing y respuesta del agente
    target_agent_name = chat.route_message(message)
    reply = chat.agent_reply(message, target_agent_name)
    logger.info(f"💬 Agent reply ({target_agent_name}): {reply}")

    # Enviar la respuesta a WhatsApp
    try:
        await send_text(to=from_number, body=reply, reply_to=reply_to_id)
        logger.info(f"✅ Mensaje enviado a {from_number}")
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje: {e}")

    return {"status": "ok"}
