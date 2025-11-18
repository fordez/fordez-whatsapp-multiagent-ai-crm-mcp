import logging
from typing import Optional

import httpx

logger = logging.getLogger("whatsapp")


async def send_web_message(
    session_id: str,
    message: str,
    webhook_url: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> bool:
    """
    Envía un mensaje de respuesta al canal web.

    Args:
        session_id: Identificador único de la sesión del usuario web
        message: Texto del mensaje a enviar
        webhook_url: URL del webhook del cliente web (opcional)
        metadata: Datos adicionales del mensaje

    Returns:
        bool: True si el envío fue exitoso, False en caso contrario
    """
    try:
        if not (session_id and message):
            logger.warning(f"Mensaje web a {session_id}: Datos incompletos")
            return False

        # Estructura del payload de respuesta
        response_payload = {
            "session_id": session_id,
            "message": message,
            "timestamp": metadata.get("timestamp") if metadata else None,
            "type": "text",
            "metadata": metadata or {},
        }

        # Si hay webhook_url, enviar la respuesta al cliente
        if webhook_url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook_url,
                    json=response_payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                logger.info(f"Mensaje web a {session_id}: Entrega exitosa")
                return True
        else:
            # Si no hay webhook_url, solo registrar (para websockets u otro método)
            logger.info(f"Mensaje web a {session_id}: Preparado para entrega")
            return True

    except httpx.HTTPError as e:
        logger.error(f"Mensaje web a {session_id}: Error HTTP - {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Mensaje web a {session_id}: Error inesperado - {str(e)}")
        return False


async def send_web_typing_indicator(
    session_id: str, webhook_url: Optional[str] = None
) -> bool:
    """
    Envía indicador de escritura al canal web.

    Args:
        session_id: Identificador único de la sesión
        webhook_url: URL del webhook del cliente

    Returns:
        bool: True si fue exitoso
    """
    try:
        if not session_id:
            return False

        typing_payload = {
            "session_id": session_id,
            "type": "typing",
            "status": "typing",
        }

        if webhook_url:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    webhook_url,
                    json=typing_payload,
                    headers={"Content-Type": "application/json"},
                )

        logger.info(f"Indicador de escritura enviado a sesión web: {session_id}")
        return True

    except Exception as e:
        logger.error(f"Error enviando typing indicator web: {str(e)}")
        return False
