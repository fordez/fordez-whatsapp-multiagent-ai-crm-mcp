import hmac
import hashlib
from fastapi import HTTPException
from config import APP_SECRET, logger


def verify_signature(body: bytes, signature: str):
    """
    Verify request authenticity using HMAC SHA256.
    """
    if not signature:
        raise HTTPException(status_code=403, detail="Signature missing")

    expected = (
        "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    )

    if not hmac.compare_digest(expected, signature):
        logger.error(
            f"❌ Invalid signature\nExpected: {expected}\nReceived: {signature}"
        )
        raise HTTPException(status_code=403, detail="Invalid signature")
