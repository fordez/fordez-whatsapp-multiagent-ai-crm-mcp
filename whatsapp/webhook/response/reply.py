import os
import asyncio
import aiohttp

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")           # Bearer token
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")         # ID del número de empresa

API_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

async def send_text(to: str, body: str, *, preview_url: bool = False, reply_to: str | None = None):
    """
    Envía un mensaje de texto por WhatsApp Cloud API.
    - to: número del usuario en formato internacional (ej. '573001234567')
    - body: texto del mensaje (hasta 4096+ caracteres)
    - preview_url: si True, intenta renderizar la vista previa del primer URL en 'body'
    - reply_to: si se pasa el wamid del mensaje del usuario, envía una 'respuesta contextual'
    """
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": body,
            "preview_url": preview_url
        }
    }

    if reply_to:
        payload["context"] = {"message_id": reply_to}

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=payload, headers=headers) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise RuntimeError(f"WhatsApp API error {resp.status}: {data}")
            return data

# ------------------ Ejemplos de uso ------------------

async def main():
    # 1) Texto simple
    await send_text("573001234567", "Hola 👋, ¿en qué te ayudo?")

    # 2) Texto con vista previa del primer URL en el cuerpo
    await send_text("573001234567", "Mira esto: https://www.whatsapp.com/", preview_url=True)

    # 3) Responder 'contextualmente' a un mensaje del usuario (usa su wamid)
    await send_text("573001234567", "Te respondo sobre ese punto 👍", reply_to="wamid.HBgMNTczMDAxMjM0NTY3FQIAERgS...")

# asyncio.run(main())
