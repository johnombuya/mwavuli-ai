"""
Audit logging for Project Mwavuli.

Writes immutable audit events to a dedicated collection so that
every significant action (exports, status changes, alerts, logins) is
traceable for governance and compliance. All database access goes
through the ReportRepository abstraction.
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, Optional

from utils.db import get_repository


def log_audit_event(
    action: str,
    user_id: str = "system",
    details: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Append an audit event.

    Args:
        action:  e.g. export_analytics, update_report_status, alert_fired, login
        user_id: Identifier of the actor (hashed API key, username, or "system")
        details: Arbitrary metadata dict
        api_key: Raw API key (will be stored as a hash prefix, not in cleartext)

    Returns:
        The document/row ID, or None on failure.
    """
    entry: Dict[str, Any] = {
        "timestamp": datetime.utcnow(),
        "action": action,
        "user_id": user_id,
    }
    if details:
        entry["details"] = details
    if api_key:
        entry["api_key_hash"] = hashlib.sha256(api_key.encode()).hexdigest()[:12]

    return get_repository().write_audit_log(entry)
