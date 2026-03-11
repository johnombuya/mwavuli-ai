"""
Backfill script for report_aggregates.

This script recomputes daily aggregate documents from existing reports
for a given date range using the provider-agnostic repository.

Usage (from backend/ directory, with venv activated):
    python scripts/backfill_aggregates.py --start-date 2024-01-01 --end-date 2024-01-31
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Tuple

_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_backend_root / ".env")

from utils.db import get_repository  # noqa: E402
from utils.db_helpers import (  # noqa: E402
    default_aggregate_doc,
    build_aggregate_update,
    apply_aggregate_increment,
)


def _parse_date(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid date {value}: {e}")


def _range_days(start: datetime, end: datetime):
    cur = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end_norm = end.replace(hour=0, minute=0, second=0, microsecond=0)
    while cur <= end_norm:
        yield cur
        cur += timedelta(days=1)


def backfill_aggregates(start_date: datetime, end_date: datetime, dry_run: bool = False) -> None:
    repo = get_repository()
    if not repo.is_connected():
        raise SystemExit("Database not available")

    total_days = 0
    for day_start in _range_days(start_date, end_date):
        day_end = day_start + timedelta(days=1)
        date_str = day_start.strftime("%Y-%m-%d")
        print(f"[backfill] Processing day {date_str}")
        total_days += 1

        reports = repo.query_reports(
            start_date=day_start,
            end_date=day_end,
            order_by_timestamp="asc",
        )

        agg_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for data in reports:
            sector = data.get("sector", "political")
            org_id = data.get("org_id") or "default"
            key = (sector, org_id)
            if key not in agg_by_key:
                agg_by_key[key] = default_aggregate_doc(date_str, sector, org_id)
            update = build_aggregate_update(data)
            apply_aggregate_increment(agg_by_key[key], update)

        if not agg_by_key:
            print(f"[backfill] No reports for {date_str}, skipping")
            continue

        for (sector, org_id), agg_doc in agg_by_key.items():
            doc_id = f"{date_str}-{sector}-{org_id}"
            print(f"[backfill]  -> {doc_id}")
            if not dry_run:
                repo.save_aggregate(doc_id, agg_doc)

    print(f"[backfill] Completed for {total_days} day(s)")


def main():
    parser = argparse.ArgumentParser(description="Backfill report_aggregates from reports.")
    parser.add_argument("--start-date", type=_parse_date, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=_parse_date, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write aggregates")
    args = parser.parse_args()

    if args.end_date < args.start_date:
        raise SystemExit("end-date must be >= start-date")

    backfill_aggregates(args.start_date, args.end_date, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
