"""
Shared emergency mode flag.

This lives outside main.py so that other modules (alerts, analyzer)
can read the current state without importing the FastAPI app.
"""

import os

_emergency_mode: bool = os.getenv("EMERGENCY_MODE", "false").lower() == "true"


def get_emergency_mode() -> bool:
    return _emergency_mode


def set_emergency_mode(enabled: bool) -> None:
    global _emergency_mode
    _emergency_mode = enabled
