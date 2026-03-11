"""
Backfill text embeddings for existing reports in Supabase.

Reads all reports that have text but no embedding, computes embeddings
using sentence-transformers, and writes them back in batches.

Usage:
  python scripts/backfill_embeddings.py [--batch-size 100] [--limit 0]

Requires: sentence-transformers, supabase. Run migration 002 first.
"""

import argparse
import os
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv
load_dotenv(_backend_root / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill report embeddings")
    parser.add_argument("--batch-size", type=int, default=100, help="Reports per batch")
    parser.add_argument("--limit", type=int, default=0, help="Max reports to process (0=all)")
    args = parser.parse_args()

    from supabase import create_client
    from models.embedder import embed_batch

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        return 1

    client = create_client(url, key)

    # Count reports needing embeddings
    total_result = (
        client.table("reports")
        .select("id", count="exact")
        .is_("embedding", "null")
        .neq("text", "")
        .execute()
    )
    total_count = total_result.count or 0
    if args.limit > 0:
        total_count = min(total_count, args.limit)
    print(f"Reports needing embeddings: {total_count}")
    if total_count == 0:
        print("Nothing to backfill.")
        return 0

    processed = 0
    offset = 0
    batch_size = args.batch_size

    while processed < total_count:
        result = (
            client.table("reports")
            .select("id, text")
            .is_("embedding", "null")
            .neq("text", "")
            .order("timestamp", desc=True)
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            break

        texts = [r["text"] for r in rows]
        embeddings = embed_batch(texts, batch_size=batch_size)

        updated = 0
        for row, emb in zip(rows, embeddings):
            if emb is None:
                continue
            vec_str = "[" + ",".join(str(x) for x in emb) + "]"
            client.table("reports").update(
                {"embedding": vec_str}
            ).eq("id", row["id"]).execute()
            updated += 1

        processed += updated
        print(f"  Batch: {updated} updated ({processed}/{total_count})")

        if len(rows) < batch_size:
            break

    print(f"Done. Backfilled {processed} report embeddings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
