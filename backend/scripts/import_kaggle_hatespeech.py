"""
Import edwardombui/hatespeech-kenya from Kaggle into Mwavuli by POSTing each row
to POST /api/v1/verify/text. Backend runs the full pipeline and saves reports.

Run from backend root with the API server running, e.g.:
  python scripts/import_kaggle_hatespeech.py [--limit N] [--dry-run] [--delay SECS]

Requires: kagglehub, pandas. Start API first (e.g. uvicorn app.main:app).
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

import kagglehub
import pandas as pd

# API text max length (VerifyTextRequest)
MAX_TEXT_LENGTH = 5000

# Sender ID used for all imported rows (anonymized in DB)
SENDER_ID = "kaggle_hatespeech_kenya"


def find_text_column(df: pd.DataFrame) -> str:
    """Detect which column contains the post/tweet text (case-insensitive)."""
    preferred = ["tweet", "text", "message", "content", "body", "comment"]
    for name in preferred:
        for col in df.columns:
            if col.lower() == name:
                return col
    return df.columns[0]


def normalize_tweet_text(raw: str) -> str:
    """
    Extract plain text from cell value. Handles list-like strings from the
    dataset (e.g. "['The political elite...']") by stripping the outer list.
    """
    s = str(raw).strip()
    if not s:
        return s
    # Strip Python list representation: ['...'] or ["..."]
    if s.startswith("['") and s.endswith("']"):
        s = s[2:-2].replace("\\'", "'")
    elif s.startswith('["') and s.endswith('"]'):
        s = s[2:-2].replace('\\"', '"')
    return s.strip()


def find_county_column(df: pd.DataFrame) -> str | None:
    """Detect optional county/location column."""
    for col in ["county", "location", "region", "place"]:
        if col in df.columns:
            return col
    return None


def post_verify(
    base_url: str, text: str, county: str | None
) -> tuple[bool, int, str | None]:
    """
    POST one text to /api/v1/verify/text.
    Returns (success, status_code, error_detail).
    """
    url = f"{base_url.rstrip('/')}/api/v1/verify/text"
    body = {
        "text": text[:MAX_TEXT_LENGTH],
        "sender_id": SENDER_ID,
    }
    if county and str(county).strip():
        low = str(county).strip().lower()
        if low != "nan":
            body["county"] = str(county).strip()

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            if 200 <= resp.getcode() < 300:
                return True, resp.getcode(), None
            err = resp.read().decode("utf-8", errors="replace")
            return False, resp.getcode(), err
    except urllib.error.HTTPError as e:
        return False, e.code, e.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        return False, 0, str(e.reason) if e.reason else str(e)
    except Exception as e:
        return False, 0, str(e)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import Kaggle hatespeech-kenya into Mwavuli via verify/text"
    )
    default_url = os.environ.get("MWAVULI_API_URL", "http://localhost:8000")
    parser.add_argument(
        "--base-url",
        default=default_url,
        help="Mwavuli API base URL (default: MWAVULI_API_URL or localhost:8000)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of rows to import (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Download and show columns/sample only; do not POST",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Seconds to wait between requests (default: 0)",
    )
    args = parser.parse_args()

    print("Downloading dataset edwardombui/hatespeech-kenya...")
    path = kagglehub.dataset_download("edwardombui/hatespeech-kenya")
    print(f"Downloaded to: {path}")

    # Find first CSV or TSV
    filepath = None
    for name in sorted(os.listdir(path)):
        if name.endswith(".csv"):
            filepath = os.path.join(path, name)
            break
        if name.endswith(".tsv"):
            filepath = os.path.join(path, name)
            break
    if not filepath:
        print("No CSV/TSV found. Files:", os.listdir(path))
        return 1

    sep = "\t" if filepath.endswith(".tsv") else ","
    nrows = args.limit
    df = pd.read_csv(
        filepath,
        sep=sep,
        nrows=nrows,
        encoding="utf-8",
        on_bad_lines="skip",
    )
    text_col = find_text_column(df)
    county_col = find_county_column(df)

    df = df.dropna(subset=[text_col])
    df[text_col] = df[text_col].astype(str).apply(normalize_tweet_text)
    df = df[df[text_col].str.len() > 0]

    print(f"Text column: {text_col}, County column: {county_col or 'none'}")
    print(f"Columns: {list(df.columns)}")
    print(f"Rows to process: {len(df)}")

    if args.dry_run:
        print("Dry run: no HTTP calls.")
        print(df.head().to_string())
        if len(df) > 0:
            sample = df.iloc[0]
            text = normalize_tweet_text(sample[text_col])[:MAX_TEXT_LENGTH]
            county = sample[county_col] if county_col else None
            body = {"text": text, "sender_id": SENDER_ID}
            if county and str(county).strip().lower() not in ("", "nan"):
                body["county"] = str(county).strip()
            sample_json = json.dumps(body, ensure_ascii=False)[:200] + "..."
            print("Sample request body:", sample_json)
        return 0

    succeeded = 0
    failed = 0
    skipped = 0

    for idx, row in df.iterrows():
        text = normalize_tweet_text(row[text_col])
        if not text:
            skipped += 1
            continue
        text = text[:MAX_TEXT_LENGTH]
        county = str(row[county_col]).strip() if county_col else None

        ok, code, detail = post_verify(args.base_url, text, county)
        if ok:
            succeeded += 1
        else:
            failed += 1
            if code >= 500:
                # Retry once after short delay
                time.sleep(1.0)
                ok2, code2, _ = post_verify(args.base_url, text, county)
                if ok2:
                    succeeded += 1
                    failed -= 1
                else:
                    msg = detail[:120] if detail else "unknown"
                    print(f"Row {idx}: HTTP {code2} - {msg}")
            else:
                msg = detail[:120] if detail else "unknown"
                print(f"Row {idx}: HTTP {code} - {msg}")

        if args.delay > 0:
            time.sleep(args.delay)

        if (succeeded + failed) % 500 == 0 and (succeeded + failed) > 0:
            print(f"Progress: {succeeded} ok, {failed} fail, {skipped} skip")

    print(f"Done. Ok: {succeeded}, Fail: {failed}, Skip: {skipped}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
