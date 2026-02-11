#!/usr/bin/env python3
"""
Run one ingestion cycle (fetch -> dedupe -> filter -> verify -> save).

Use from backend directory:
  python scripts/run_ingestion.py

Or schedule with cron (e.g. every 30 minutes):
  0,30 * * * * cd /path/to/backend && python scripts/run_ingestion.py

Requires .env with INGESTION_ENABLED=true and optional INGESTION_RSS_FEEDS, etc.
"""

import asyncio
import os
import sys

# Ensure backend root is on path
_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

os.chdir(_backend)


async def main() -> None:
    from app.ingestion.pipeline import run_pipeline
    from utils.ingestion_config import get_job_id
    from utils.db import set_ingestion_last_run

    counts = await run_pipeline()
    job_id = get_job_id() or ""
    set_ingestion_last_run(counts, job_id)
    print("[ingestion] Run complete:", counts)


if __name__ == "__main__":
    asyncio.run(main())
