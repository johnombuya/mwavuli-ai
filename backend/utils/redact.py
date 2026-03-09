"""
PII redaction utilities for Project Mwavuli.

Strips personally identifiable information (phone numbers, national IDs,
email addresses) from text before it is persisted in Firestore.
"""

import re

# Kenyan phone: +254XXXXXXXXX, 254XXXXXXXXX, 07XXXXXXXX, 01XXXXXXXX
_PHONE_RE = re.compile(
    r"(?:\+?254|0)[17]\d{8}"
)

# Kenyan national ID: 8-digit number (standalone)
_NATIONAL_ID_RE = re.compile(r"\b\d{8}\b")

# Email addresses
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
)

_PLACEHOLDER = "[REDACTED]"


def redact_pii(text: str) -> str:
    """Replace phone numbers, national IDs, and emails with [REDACTED]."""
    text = _PHONE_RE.sub(_PLACEHOLDER, text)
    text = _EMAIL_RE.sub(_PLACEHOLDER, text)
    text = _NATIONAL_ID_RE.sub(_PLACEHOLDER, text)
    return text
