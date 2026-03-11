"""
Export all Firestore data to local JSON files for offline migration.

Usage (from backend/ directory):
    python scripts/export_firebase_to_json.py [--output-dir ./firebase_export]

This reads all documents from Firestore using paginated queries and writes
them to JSON files. NOTE: This DOES consume Firestore read quota -- use
``gcloud firestore export`` for a zero-quota alternative (see plan docs).

Zero-quota alternative:
    gcloud firestore export gs://YOUR_BUCKET/mwavuli-export \\
        --database=mwavuli-nira-db \\
        --collection-ids=reports,report_aggregates,audit_logs,report_appeals
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")
sys.path.insert(0, str(_backend_root))


def _serialize(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def _export_collection(db, collection_path: str, output_file: Path, batch_size: int = 500):
    """Export a single Firestore collection to a JSON file."""
    parts = collection_path.split("/")
    ref = db
    for i, part in enumerate(parts):
        if i % 2 == 0:
            ref = ref.collection(part)
        else:
            ref = ref.document(part)

    print(f"  Exporting {collection_path} ...")
    docs = []
    last_doc = None
    total = 0

    while True:
        query = ref.order_by("__name__").limit(batch_size)
        if last_doc:
            query = query.start_after(last_doc)

        batch = list(query.stream())
        if not batch:
            break

        for doc in batch:
            d = doc.to_dict()
            d["__id__"] = doc.id
            docs.append(d)

        total += len(batch)
        last_doc = batch[-1]
        print(f"    ... {total} documents so far")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(docs, f, default=_serialize, indent=2)
    print(f"  -> Wrote {total} documents to {output_file}")
    return total


def main():
    parser = argparse.ArgumentParser(description="Export Firestore data to JSON files")
    parser.add_argument(
        "--output-dir", type=str, default="./firebase_export",
        help="Output directory for JSON files (default: ./firebase_export)",
    )
    args = parser.parse_args()

    os.environ["DB_PROVIDER"] = "firebase"
    from utils.db_firebase import FirebaseRepository

    repo = FirebaseRepository()
    db = repo._get_db()
    if db is None:
        raise SystemExit("Failed to connect to Firestore. Check your credentials.")

    output_dir = Path(args.output_dir)

    base_path = "artifacts/mwavuli/public/data"
    collections = {
        "reports": f"{base_path}/reports",
        "report_aggregates": f"{base_path}/report_aggregates",
        "audit_logs": f"{base_path}/audit_logs",
        "report_appeals": f"{base_path}/report_appeals",
        "ingestion_audit": f"{base_path}/ingestion_audit",
        "ingestion_status": f"{base_path}/ingestion_status",
    }

    grand_total = 0
    for name, path in collections.items():
        count = _export_collection(db, path, output_dir / f"{name}.json")
        grand_total += count

    print(f"\nExport complete: {grand_total} total documents in {output_dir}")


if __name__ == "__main__":
    main()
