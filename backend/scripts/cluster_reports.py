"""
Discover narrative clusters from report embeddings using HDBSCAN.

Reads reports from the last N days, clusters their embeddings, computes
per-cluster metadata (keywords, counties, risk breakdown, time span),
and writes results to the report_clusters table.

Usage:
  python scripts/cluster_reports.py [--days 7] [--min-cluster-size 5]

Requires: scikit-learn, supabase. Run migrations 002 and 003 first.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv
load_dotenv(_backend_root / ".env")

STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "and", "but", "or", "nor", "not", "so", "yet", "for", "to", "of",
    "in", "on", "at", "by", "from", "with", "that", "this", "these",
    "those", "it", "its", "he", "she", "we", "they", "you", "i", "me",
    "him", "her", "us", "them", "my", "your", "his", "our", "their",
    "what", "which", "who", "whom", "when", "where", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "any", "no", "than", "too", "very", "just", "about",
    "na", "ya", "wa", "ni", "kwa", "au", "hii", "huo", "yake",
    "http", "https", "www", "com",
})


def _extract_keywords(texts: list[str], top_n: int = 10) -> list[str]:
    """Extract top keywords from a list of texts using simple TF counting."""
    counter: Counter = Counter()
    for text in texts:
        tokens = re.findall(r"[a-zA-Z\u00C0-\u024F]{3,}", text.lower())
        for t in tokens:
            if t not in STOP_WORDS and len(t) >= 3:
                counter[t] += 1
    return [word for word, _ in counter.most_common(top_n)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Cluster reports by embedding similarity")
    parser.add_argument("--days", type=int, default=7, help="Look back N days")
    parser.add_argument("--min-cluster-size", type=int, default=5, help="HDBSCAN min_cluster_size")
    args = parser.parse_args()

    from sklearn.cluster import HDBSCAN
    from supabase import create_client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        return 1

    client = create_client(url, key)
    cutoff = (datetime.utcnow() - timedelta(days=args.days)).isoformat()

    # Fetch reports with embeddings
    print(f"Fetching reports with embeddings from the last {args.days} days...")
    all_rows: list[dict] = []
    offset = 0
    batch = 1000
    while True:
        result = (
            client.table("reports")
            .select("id, text, risk_level, county, timestamp, sender_hash, embedding")
            .not_.is_("embedding", "null")
            .gte("timestamp", cutoff)
            .order("timestamp", desc=True)
            .range(offset, offset + batch - 1)
            .execute()
        )
        rows = result.data or []
        all_rows.extend(rows)
        if len(rows) < batch:
            break
        offset += batch

    print(f"Fetched {len(all_rows)} reports with embeddings.")
    if len(all_rows) < args.min_cluster_size * 2:
        print("Not enough reports to cluster meaningfully.")
        return 0

    # Parse embeddings into numpy array
    embeddings = []
    valid_rows = []
    for r in all_rows:
        emb = r.get("embedding")
        if isinstance(emb, str):
            emb = json.loads(emb)
        if isinstance(emb, list) and len(emb) > 0:
            embeddings.append(emb)
            valid_rows.append(r)

    if len(embeddings) < args.min_cluster_size * 2:
        print("Not enough valid embeddings.")
        return 0

    X = np.array(embeddings, dtype=np.float32)
    print(f"Clustering {X.shape[0]} embeddings...")

    clusterer = HDBSCAN(
        min_cluster_size=args.min_cluster_size,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    labels = clusterer.fit_predict(X)

    unique_labels = set(labels)
    unique_labels.discard(-1)  # -1 is noise
    print(f"Found {len(unique_labels)} clusters ({(labels == -1).sum()} noise points).")

    if not unique_labels:
        print("No clusters found.")
        return 0

    # Mark old clusters as inactive
    client.table("report_clusters").update(
        {"is_active": False}
    ).eq("is_active", True).execute()

    computed_at = datetime.utcnow().isoformat()
    inserted = 0

    for label in sorted(unique_labels):
        mask = labels == label
        cluster_rows = [valid_rows[i] for i in range(len(valid_rows)) if mask[i]]
        cluster_embeddings = X[mask]

        texts = [r.get("text", "") for r in cluster_rows]
        keywords = _extract_keywords(texts)

        county_dist = dict(Counter(r.get("county", "unknown") for r in cluster_rows))
        risk_dist = dict(Counter(r.get("risk_level", "UNKNOWN") for r in cluster_rows))

        timestamps = []
        for r in cluster_rows:
            ts = r.get("timestamp")
            if ts:
                timestamps.append(ts)
        timestamps.sort()

        # Representative text: closest to centroid
        centroid = cluster_embeddings.mean(axis=0)
        dists = np.linalg.norm(cluster_embeddings - centroid, axis=1)
        rep_idx = int(dists.argmin())
        representative = texts[rep_idx][:500]

        row = {
            "computed_at": computed_at,
            "cluster_label": int(label),
            "size": len(cluster_rows),
            "representative_text": representative,
            "top_keywords": keywords,
            "county_distribution": county_dist,
            "risk_breakdown": risk_dist,
            "first_seen": timestamps[0] if timestamps else None,
            "last_seen": timestamps[-1] if timestamps else None,
            "is_active": True,
        }
        client.table("report_clusters").insert(row).execute()
        inserted += 1
        print(f"  Cluster {label}: {len(cluster_rows)} reports, keywords: {keywords[:5]}")

    print(f"Done. Inserted {inserted} clusters.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
