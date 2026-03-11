"""
Migrate exported Firebase data into Supabase.

Usage (from backend/ directory):
    1. Export Firebase data first:
       python scripts/export_firebase_to_json.py --output-dir ./firebase_export

    2. Run this migration:
       python scripts/migrate_to_supabase.py --input-dir ./firebase_export [--dry-run]

Prerequisite: Run the SQL migration in Supabase first:
    backend/migrations/001_initial_schema.sql

This script reads the JSON files produced by export_firebase_to_json.py
and batch-inserts them into Supabase using upserts for safe re-runs.
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")
sys.path.insert(0, str(_backend_root))


def _parse_timestamp(val):
    """Convert various timestamp formats to ISO string."""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        # Firestore REST export format: {"_seconds": ..., "_nanoseconds": ...}
        seconds = val.get("_seconds") or val.get("seconds")
        if seconds:
            return datetime.utcfromtimestamp(int(seconds)).isoformat()
    if isinstance(val, (int, float)):
        return datetime.utcfromtimestamp(val).isoformat()
    return str(val)


def _ensure_uuid(doc_id: str) -> str:
    """If the ID isn't a valid UUID, derive one deterministically."""
    try:
        uuid.UUID(doc_id)
        return doc_id
    except (ValueError, AttributeError):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"mwavuli:{doc_id}"))


def _transform_report(doc: dict) -> dict:
    """Transform a Firebase report document for Supabase insertion."""
    doc_id = doc.pop("__id__", None)
    row = {
        "id": _ensure_uuid(doc_id) if doc_id else str(uuid.uuid4()),
        "text": doc.get("text", ""),
        "risk_level": doc.get("risk_level", "UNKNOWN"),
        "language": doc.get("language", "auto-detect"),
        "county": doc.get("county", "unknown"),
        "timestamp": _parse_timestamp(doc.get("timestamp")),
        "sender_hash": doc.get("sender_hash"),
        "sector": doc.get("sector", "political"),
        "status": doc.get("status", "pending"),
        "hour_of_day": doc.get("hour_of_day"),
        "day_of_week": doc.get("day_of_week"),
        "is_weekend": doc.get("is_weekend", False),
        "text_length": doc.get("text_length", 0),
        "word_count": doc.get("word_count", 0),
        "has_urls": doc.get("has_urls", False),
        "has_mentions": doc.get("has_mentions", False),
        "detection_method": doc.get("detection_method"),
        "confidence_score": doc.get("confidence_score"),
        "matched_keyword": doc.get("matched_keyword"),
        "gemini_context_flag": doc.get("gemini_context_flag", False),
        "region": doc.get("region", "Unknown"),
        "is_urban": doc.get("is_urban", False),
        "scores": json.dumps(doc.get("scores")) if doc.get("scores") else None,
        "org_id": doc.get("org_id", "default"),
        "source_type": doc.get("source_type"),
        "source_url": doc.get("source_url"),
        "content_hash": doc.get("content_hash"),
        "created_by": doc.get("created_by"),
        "ingestion_job_id": doc.get("ingestion_job_id"),
        "explanation": doc.get("explanation"),
        "explanation_details": (
            json.dumps(doc.get("explanation_details"))
            if doc.get("explanation_details") else None
        ),
        "kenyan_model_risk": doc.get("kenyan_model_risk"),
        "kenyan_model_score": doc.get("kenyan_model_score"),
        "coordinated_campaign": doc.get("coordinated_campaign", False),
        "recommended_action": doc.get("recommended_action"),
    }
    return {k: v for k, v in row.items() if v is not None}


def _transform_aggregate(doc: dict) -> dict:
    """Transform a Firebase aggregate doc for Supabase."""
    doc_id = doc.pop("__id__", None) or ""
    return {
        "id": doc_id,
        "date": doc.get("date"),
        "sector": doc.get("sector", "political"),
        "org_id": doc.get("org_id", "default"),
        "risk_counts": doc.get("risk_counts", {}),
        "keyword_counts": doc.get("keyword_counts", {}),
        "county_counts": doc.get("county_counts", {}),
        "toxicity": doc.get("toxicity", {"sum": 0, "count": 0}),
        "status_counts": doc.get("status_counts", {}),
        "detection_method_counts": doc.get("detection_method_counts", {}),
        "url_mention_counts": doc.get("url_mention_counts", {}),
    }


def _transform_audit(doc: dict) -> dict:
    doc_id = doc.pop("__id__", None)
    return {
        "id": _ensure_uuid(doc_id) if doc_id else str(uuid.uuid4()),
        "timestamp": _parse_timestamp(doc.get("timestamp")),
        "action": doc.get("action", ""),
        "user_id": doc.get("user_id", "system"),
        "details": json.dumps(doc.get("details")) if doc.get("details") else None,
        "api_key_hash": doc.get("api_key_hash"),
        "prev_hash": doc.get("prev_hash"),
    }


def _transform_appeal(doc: dict) -> dict:
    doc_id = doc.pop("__id__", None)
    return {
        "id": _ensure_uuid(doc_id) if doc_id else str(uuid.uuid4()),
        "report_id": doc.get("report_id", ""),
        "reason": doc.get("reason", ""),
        "status": doc.get("status", "pending"),
        "timestamp": _parse_timestamp(doc.get("timestamp")),
        "original_risk_level": doc.get("original_risk_level"),
        "resolution": doc.get("resolution"),
        "resolved_at": _parse_timestamp(doc.get("resolved_at")),
        "notes": doc.get("notes"),
    }


def _batch_upsert(client, table: str, rows: list, batch_size: int = 200):
    """Upsert rows in batches. Returns total count."""
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        client.table(table).upsert(batch).execute()
        total += len(batch)
        print(f"    ... {total}/{len(rows)}")
    return total


def migrate(input_dir: Path, dry_run: bool = False):
    from supabase import create_client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

    client = create_client(url, key)
    print(f"Connected to Supabase at {url}")

    table_map = {
        "reports": ("reports.json", _transform_report),
        "report_aggregates": ("report_aggregates.json", _transform_aggregate),
        "audit_logs": ("audit_logs.json", _transform_audit),
        "report_appeals": ("report_appeals.json", _transform_appeal),
    }

    for table, (filename, transform_fn) in table_map.items():
        filepath = input_dir / filename
        if not filepath.exists():
            print(f"  Skipping {table}: {filepath} not found")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            docs = json.load(f)

        print(f"\n  Migrating {len(docs)} docs -> {table}")
        rows = [transform_fn(doc) for doc in docs]

        if dry_run:
            print(f"    [dry-run] Would insert {len(rows)} rows into {table}")
            if rows:
                print(f"    Sample row: {json.dumps(rows[0], indent=2, default=str)[:500]}")
        else:
            count = _batch_upsert(client, table, rows)
            print(f"    -> Inserted {count} rows into {table}")

    # Handle ingestion_audit and ingestion_status separately
    for filename, table in [
        ("ingestion_audit.json", "ingestion_audit"),
        ("ingestion_status.json", "ingestion_status"),
    ]:
        filepath = input_dir / filename
        if not filepath.exists():
            print(f"  Skipping {table}: {filepath} not found")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            docs = json.load(f)

        print(f"\n  Migrating {len(docs)} docs -> {table}")
        rows = []
        for doc in docs:
            doc_id = doc.pop("__id__", None)
            for k, v in doc.items():
                if isinstance(v, dict) and ("_seconds" in v or "seconds" in v):
                    doc[k] = _parse_timestamp(v)
            if table == "ingestion_status":
                doc["id"] = doc_id or "last_run"
            else:
                doc["id"] = _ensure_uuid(doc_id) if doc_id else str(uuid.uuid4())
                doc["timestamp"] = _parse_timestamp(doc.get("timestamp"))
            rows.append(doc)

        if dry_run:
            print(f"    [dry-run] Would insert {len(rows)} rows into {table}")
        else:
            count = _batch_upsert(client, table, rows)
            print(f"    -> Inserted {count} rows into {table}")

    print("\nMigration complete!")


def main():
    parser = argparse.ArgumentParser(description="Migrate Firebase export data to Supabase")
    parser.add_argument(
        "--input-dir", type=str, default="./firebase_export",
        help="Directory containing exported JSON files",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise SystemExit(f"Input directory not found: {input_dir}")

    migrate(input_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
