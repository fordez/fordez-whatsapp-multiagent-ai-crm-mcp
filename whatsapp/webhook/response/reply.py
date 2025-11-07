import aiohttp


async def send_text(
    to: str,
    body: str,
    *,
    preview_url: bool = False,
    reply_to: str | None = None,
    token: str = None,
    phone_number_id: str = None,
):
    token = token  # siempre lo recibes desde route.py
    phone_number_id = phone_number_id

    API_URL = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body, "preview_url": preview_url},
    }

    if reply_to:
        payload["context"] = {"message_id": reply_to}

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=payload, headers=headers) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise RuntimeError(f"WhatsApp API error {resp.status}: {data}")
            return data
