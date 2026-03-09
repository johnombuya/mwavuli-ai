"""
Purge reports older than DATA_RETENTION_DAYS from Firestore.

Run periodically via cron/task-scheduler:
  python scripts/purge_expired_reports.py [--dry-run]
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")
sys.path.insert(0, str(_backend_root))

from utils.db import _get_db  # noqa: E402


def purge(dry_run: bool = False) -> int:
    retention_days = int(os.getenv("DATA_RETENTION_DAYS", "365"))
    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    db = _get_db()
    if db is None:
        print("Firestore not connected — nothing to purge.")
        return 1

    reports_ref = (
        db.collection("artifacts")
        .document("mwavuli")
        .collection("public")
        .document("data")
        .collection("reports")
    )

    query = reports_ref.where("timestamp", "<", cutoff).limit(500)
    deleted = 0

    while True:
        docs = list(query.stream())
        if not docs:
            break
        for doc in docs:
            if dry_run:
                ts = doc.to_dict().get("timestamp", "?")
                print(f"[dry-run] Would delete {doc.id} (timestamp={ts})")
            else:
                doc.reference.delete()
            deleted += 1

    action = "Would delete" if dry_run else "Deleted"
    print(f"{action} {deleted} reports older than {retention_days} days (cutoff={cutoff.isoformat()}).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge expired Mwavuli reports")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    args = parser.parse_args()
    return purge(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
