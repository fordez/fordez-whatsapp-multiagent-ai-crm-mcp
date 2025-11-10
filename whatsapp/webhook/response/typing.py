import aiohttp


async def send_typing_indicator(message_id: str, token: str, phone_number_id: str):
    API_URL = f"https://graph.facebook.com/v24.0/{phone_number_id}/messages"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
        "typing_indicator": {"type": "text"},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=payload, headers=headers) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise RuntimeError(
                    f"WhatsApp typing indicator error {resp.status}: {data}"
                )
            return data
