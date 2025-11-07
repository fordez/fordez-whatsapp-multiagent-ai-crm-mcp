# whatsapp/webhook/route.py
from fastapi import APIRouter, HTTPException, Request, Response

from whatsapp.agent.agents import agent_service
from whatsapp.config import PHONE_NUMBER_ID, VERIFY_TOKEN, WHATSAPP_TOKEN, logger
from whatsapp.webhook.request.dispatcher import dispatch_message
from whatsapp.webhook.response.reply import send_text
from whatsapp.webhook.utilis.client_credentials import get_client_credentials

router = APIRouter()


@router.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ WEBHOOK_VERIFIED")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("❌ Verify token mismatch")
    return Response(content="verify token mismatch", status_code=403)


@router.post("/webhook")
async def receive_data(request: Request):
    # Parsear JSON
    try:
        raw_data = await request.json()
    except Exception as e:
        logger.error(f"❌ Error parsing JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # LOG de STATUS (sent, delivered, read)
    try:
        statuses = raw_data["entry"][0]["changes"][0]["value"].get("statuses", [])
        for st in statuses:
            logger.info(
                f"📊 STATUS: {st.get('status')} | recipient={st.get('recipient_id')} | timestamp={st.get('timestamp')}"
            )
    except Exception:
        pass

    # Detectar cliente por phone_number_id usando Sheets/cache
    phone_id = raw_data["entry"][0]["changes"][0]["value"]["metadata"].get(
        "phone_number_id"
    )
    client = get_client_credentials(phone_id) if phone_id else None

    if client:
        whatsapp_token = client.get("Access Token") or WHATSAPP_TOKEN
        phone_number_id = client.get("Phone Number ID") or PHONE_NUMBER_ID
        role_qualifier_id = client.get("Role Qualifier ID")
        logger.info(
            f"🟦 Cliente detectado: {client.get('Business Name')} | phone_id={phone_id}"
        )
    else:
        whatsapp_token = WHATSAPP_TOKEN
        phone_number_id = PHONE_NUMBER_ID
        role_qualifier_id = None
        logger.warning("⚠️ No se encontraron credenciales, usando fallback .env")

    # Transformar datos
    transformed_data = dispatch_message(raw_data)

    # Extraer datos
    message = transformed_data.get("message") or transformed_data.get("text")
    from_number = transformed_data.get("from")
    reply_to_id = transformed_data.get("wamid")

    if not message:
        return {"status": "no_message"}

    logger.info(f"📝 Parsed text message from {from_number}: {message}")

    # Llamar al agente
    try:
        result = await agent_service(message, role_qualifier_id=role_qualifier_id)
        reply = result.get("final_output", "Lo siento, no pude generar una respuesta.")
        logger.info(f"💬 Agent reply: {reply}")
    except Exception as e:
        logger.error(f"❌ Error generando respuesta del agente: {e}")
        reply = "Lo siento, hubo un error procesando tu mensaje."

    # Enviar respuesta usando credenciales dinámicas
    try:
        await send_text(
            to=from_number,
            body=reply,
            reply_to=reply_to_id,
            token=whatsapp_token,
            phone_number_id=phone_number_id,
        )
        logger.info(f"✅ Mensaje enviado a {from_number}")
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje: {e}")

    return {"status": "ok"}
