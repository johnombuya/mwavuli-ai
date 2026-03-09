"""
Audit logging for Project Mwavuli.

Writes immutable audit events to a dedicated Firestore collection so that
every significant action (exports, status changes, alerts, logins) is
traceable for governance and compliance.
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, Optional

from utils.db import _get_db


def _get_audit_collection():
    db = _get_db()
    if db is None:
        return None
    return (
        db.collection("artifacts")
        .document("mwavuli")
        .collection("public")
        .document("data")
        .collection("audit_logs")
    )


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
        The Firestore document ID, or None on failure.
    """
    ref = _get_audit_collection()
    if ref is None:
        return None

    entry: Dict[str, Any] = {
        "timestamp": datetime.utcnow(),
        "action": action,
        "user_id": user_id,
    }
    if details:
        entry["details"] = details
    if api_key:
        entry["api_key_hash"] = hashlib.sha256(api_key.encode()).hexdigest()[:12]

    # Hash-chain: compute hash of (previous entry id + current payload)
    try:
        last_doc = list(ref.order_by("timestamp", direction="DESCENDING").limit(1).stream())
        prev_id = last_doc[0].id if last_doc else "genesis"
    except Exception:
        prev_id = "genesis"
    import json as _json
    chain_input = prev_id + _json.dumps(entry, default=str, sort_keys=True)
    entry["prev_hash"] = hashlib.sha256(chain_input.encode()).hexdigest()[:24]

    try:
        _, doc_ref = ref.add(entry)
        return doc_ref.id
    except Exception as e:
        print(f"[audit] Failed to write audit event: {e}")
        return None
