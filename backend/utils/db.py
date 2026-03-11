"""
Database factory for Project Mwavuli.

Selects between Firebase and Supabase based on the DB_PROVIDER env var.
Exposes backward-compatible top-level functions so existing callers
(main.py, analytics.py, scripts, etc.) keep working without changes.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

from utils.db_base import ReportRepository
from utils.db_helpers import (  # noqa: F401  — re-exported for callers
    anonymize_sender as _anonymize_sender,
    normalize_text_for_hash as _normalize_text_for_hash,
    COUNTY_TO_REGION,
    URBAN_COUNTIES,
    _VALID_STATUSES,
)

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")

_repo: Optional[ReportRepository] = None


def get_repository() -> ReportRepository:
    """Return the singleton repository instance based on DB_PROVIDER."""
    global _repo
    if _repo is not None:
        return _repo

    provider = os.getenv("DB_PROVIDER", "firebase").lower()

    if provider == "supabase":
        from utils.db_supabase import SupabaseRepository
        _repo = SupabaseRepository()
    else:
        from utils.db_firebase import FirebaseRepository
        _repo = FirebaseRepository()

    return _repo


# ── Backward-compatible wrappers ─────────────────────────────────────
# These let existing code like ``from utils.db import save_report`` keep
# working without any import changes during the incremental migration.


def save_report(data: dict) -> Optional[str]:
    return get_repository().save_report(data)


def get_report(report_id: str) -> Optional[dict]:
    return get_repository().get_report(report_id)


def get_recent_reports(limit: int = 10, status: Optional[str] = None) -> list:
    return get_repository().get_recent_reports(limit, status)


def update_report_status(report_id: str, new_status: str) -> bool:
    return get_repository().update_report_status(report_id, new_status)


def report_exists_by_content_hash(content_hash: str) -> bool:
    return get_repository().report_exists_by_content_hash(content_hash)


def report_exists_by_source_url(source_url: str) -> bool:
    return get_repository().report_exists_by_source_url(source_url)


def detect_coordinated_activity(
    sender_hash: str, window_minutes: int = 60, threshold: int = 10,
) -> bool:
    return get_repository().detect_coordinated_activity(
        sender_hash, window_minutes, threshold,
    )


def is_database_connected() -> bool:
    return get_repository().is_connected()


def write_ingestion_audit(
    action: str,
    job_id: str = "",
    source_type: str = "",
    url: str = "",
    reason: str = "",
    risk_level: Optional[str] = None,
) -> None:
    entry = {
        "timestamp": datetime.utcnow(),
        "job_id": job_id,
        "action": action,
        "source_type": source_type,
        "url": url,
        "reason": reason,
    }
    if risk_level:
        entry["risk_level"] = risk_level
    get_repository().write_ingestion_audit(entry)


def set_ingestion_last_run(counts: Dict[str, Any], job_id: str = "") -> None:
    get_repository().set_ingestion_last_run({
        "timestamp": datetime.utcnow(),
        "job_id": job_id,
        "counts": counts,
    })


def get_ingestion_last_run() -> Optional[Dict[str, Any]]:
    return get_repository().get_ingestion_last_run()


# Legacy alias kept for ``from utils.db import _get_db`` in analytics.py
# and scripts that haven't migrated yet.  Returns the raw Firestore client
# ONLY when DB_PROVIDER=firebase; otherwise None.
def _get_db():
    repo = get_repository()
    if hasattr(repo, "_get_db"):
        return repo._get_db()
    return None
