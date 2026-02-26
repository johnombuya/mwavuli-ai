"""
Twilio client for sending WhatsApp replies in Project Mwavuli.

Used by the Twilio webhook to send verification results and prebunking tips
back to the user. Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and
TWILIO_WHATSAPP_FROM in environment.
"""

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from dotenv import load_dotenv

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")


def is_twilio_configured() -> bool:
    """Return True if Twilio credentials are set (non-placeholder)."""
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_num = os.getenv("TWILIO_WHATSAPP_FROM", "").strip()
    if not sid or not token or not from_num:
        return False
    if "your_" in sid.lower() or "your_" in token.lower():
        return False
    if not from_num.startswith("whatsapp:"):
        return False
    return True


def send_whatsapp_message(to: str, body: str) -> tuple[bool, Optional[str]]:
    """
    Send a WhatsApp message via Twilio.

    Args:
        to: Recipient in Twilio format, e.g. "whatsapp:+254712345678"
        body: Message text (max ~4096 chars for WhatsApp).

    Returns:
        (success: bool, error_message: Optional[str])
    """
    if not is_twilio_configured():
        return False, "Twilio is not configured (missing or placeholder env vars)."

    try:
        from twilio.rest import Client
    except ImportError:
        return False, "Twilio package not installed. Run: pip install twilio"

    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_num = os.getenv("TWILIO_WHATSAPP_FROM")

    # Ensure 'to' has whatsapp: prefix
    if not to.startswith("whatsapp:"):
        to = f"whatsapp:{to}" if to.startswith("+") else f"whatsapp:+{to}"

    try:
        client = Client(sid, token)
        client.messages.create(
            body=body[:4096],
            from_=from_num,
            to=to,
        )
        return True, None
    except Exception as e:
        return False, str(e)


def validate_twilio_signature(url: str, params: dict, signature: str) -> bool:
    """
    Validate that the request came from Twilio using the request signature.

    Args:
        url: Full webhook URL (e.g. https://your-domain.com/api/v1/webhooks/twilio)
        params: Request form body as dict (all string values)
        signature: X-Twilio-Signature header value

    Returns:
        True if signature is valid or if auth token is not set (skip validation).
    """
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    if not token or "your_" in token.lower():
        return True  # Skip validation when not configured

    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(token)
        return validator.validate(url, params, signature)
    except Exception:
        return False
