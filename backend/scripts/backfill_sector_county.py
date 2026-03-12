"""
Backfill sector and county for existing reports using a 3-tier approach.

Tier 1 (free):  String-match county names and lexicon-match sectors locally.
Tier 2:         LLM classification via Gemini (cloud) or Ollama (local).

Usage:
  python scripts/backfill_sector_county.py                          # auto engine
  python scripts/backfill_sector_county.py --engine ollama          # force Ollama
  python scripts/backfill_sector_county.py --engine gemini          # force Gemini
  python scripts/backfill_sector_county.py --skip-llm               # local-only pass
  python scripts/backfill_sector_county.py --dry-run                # preview, no writes

Requires: supabase. Tier 2 requires google-genai (gemini) or Ollama running locally.
Run migration 004 first.
"""

import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv
load_dotenv(_backend_root / ".env")

_VALID_SECTORS = {"political", "health", "security", "fraud"}
_UPDATE_THROTTLE = 0.05  # seconds between Supabase writes

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_update(client, table: str, data: dict, rid: str, retries: int = 3):
    """Update a row with retry + exponential backoff on connection errors."""
    for attempt in range(retries):
        try:
            client.table(table).update(data).eq("id", rid).execute()
            return
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"    [retry {attempt + 1}] {e} — waiting {wait}s")
                time.sleep(wait)
            else:
                print(f"    [FAIL] Could not update {rid}: {e}")


def _strip_code_fence(raw: str) -> str:
    """Remove markdown code fences from LLM responses."""
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def _parse_sector_county(entry: dict) -> dict:
    """Normalise a single LLM classification result."""
    sector = entry.get("s") or entry.get("sector")
    county = entry.get("c") or entry.get("county")
    if sector and sector not in _VALID_SECTORS:
        sector = None
    return {
        "i": entry.get("i", -1),
        "sector": sector or None,
        "county": county if county and county != "null" else None,
    }


# ---------------------------------------------------------------------------
# Gemini engine
# ---------------------------------------------------------------------------

def _init_gemini():
    """Return a Gemini client or None."""
    try:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key or api_key == "your_gemini_api_key_here":
            return None
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[gemini] Init failed: {e}")
        return None


def _call_gemini_batch(client, texts: list[dict]) -> list[dict]:
    """Classify a batch of texts via Gemini (one API call for N texts)."""
    lines = []
    for item in texts:
        clean = item["t"].replace('"', "'")[:200]
        lines.append(f'{item["i"]}:"{clean}"')

    prompt = (
        "Classify each text. Return ONLY a JSON array.\n"
        'For each: {"i":index,"s":"sector","c":"county_or_null"}\n'
        "Sectors: political, health, security, fraud.\n"
        "County: Kenyan county name or null.\n\n"
        + "\n".join(lines)
        + "\n"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = _strip_code_fence(response.text.strip())
        return [_parse_sector_county(e) for e in json.loads(raw)]
    except Exception as e:
        print(f"  [gemini] Batch error: {e}")
        return []


# ---------------------------------------------------------------------------
# Ollama engine
# ---------------------------------------------------------------------------

def _init_ollama() -> dict | None:
    """Return Ollama config dict or None if not available."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    model = os.getenv("OLLAMA_MODEL", "llama3").strip()
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5):
            pass
        print(f"[ollama] Connected to {base_url}, model={model}")
        return {"base_url": base_url, "model": model}
    except Exception as e:
        print(f"[ollama] Not reachable at {base_url}: {e}")
        return None


def _call_ollama_single(cfg: dict, text: str) -> dict:
    """Classify one text via Ollama. Returns {"sector": ..., "county": ...}."""
    prompt = (
        'Classify: sector (political/health/security/fraud) and Kenyan county or null.\n'
        f'Text: "{text[:200]}"\n'
        'Reply JSON only: {"s":"sector","c":"county_or_null"}'
    )

    body = json.dumps({
        "model": cfg["model"],
        "prompt": prompt,
        "system": "You are a JSON API. Return only valid JSON, no explanation.",
        "format": "json",
        "stream": False,
    }).encode()

    try:
        req = urllib.request.Request(
            f'{cfg["base_url"]}/api/generate',
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            raw = _strip_code_fence(data.get("response", "").strip())
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                start = raw.find("{")
                end = raw.rfind("}")
                if start != -1 and end != -1:
                    raw = raw[start:end + 1]
                raw = raw.replace("'", '"')
                parsed = json.loads(raw)
            return _parse_sector_county(parsed)
    except Exception as e:
        print(f"    [ollama] Error: {e}")
        return {"i": -1, "sector": None, "county": None}


def _call_ollama_batch(cfg: dict, texts: list[dict], workers: int = 4) -> list[dict]:
    """Classify texts concurrently via Ollama using a thread pool."""
    def _process(item: dict) -> dict:
        r = _call_ollama_single(cfg, item["t"])
        r["i"] = item["i"]
        return r

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_process, texts))
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill sector & county for reports")
    parser.add_argument("--batch-size", type=int, default=20, help="Texts per LLM batch")
    parser.add_argument("--limit", type=int, default=0, help="Max reports to process (0=all)")
    parser.add_argument("--skip-llm", action="store_true", help="Only run local matching (no LLM)")
    parser.add_argument("--skip-gemini", action="store_true", help="(deprecated) Alias for --skip-llm")
    parser.add_argument("--engine", choices=["auto", "gemini", "ollama"], default="auto",
                        help="LLM engine for Tier 2: auto (try gemini then ollama), gemini, or ollama")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between LLM batches")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent Ollama workers (default 4)")
    args = parser.parse_args()

    skip_llm = args.skip_llm or args.skip_gemini

    from supabase import create_client
    from utils.db_helpers import detect_county
    from utils.lexicon import detect_sector

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        return 1

    client = create_client(url, key)

    # ---- Fetch reports ----
    print("Fetching reports...")
    all_reports: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        batch = (
            client.table("reports")
            .select("id,text,county,sector")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = batch.data or []
        if not rows:
            break
        all_reports.extend(rows)
        offset += page_size
        if args.limit and len(all_reports) >= args.limit:
            all_reports = all_reports[: args.limit]
            break

    print(f"Fetched {len(all_reports)} reports total.")

    # ---- Tier 1: Local matching ----
    needs_llm: list[dict] = []
    local_updates = 0
    total = len(all_reports)

    for idx, report in enumerate(all_reports):
        if (idx + 1) % 500 == 0:
            print(f"  Tier 1 progress: {idx + 1}/{total} ({local_updates} updated so far)")
        rid = report["id"]
        text = report.get("text") or ""
        current_county = (report.get("county") or "unknown").strip()
        current_sector = (report.get("sector") or "political").strip()

        new_county = None
        new_sector = None

        if current_county == "unknown":
            new_county = detect_county(text)

        if current_sector == "political":
            new_sector = detect_sector(text)

        if new_county or new_sector:
            update_data: dict = {}
            if new_county:
                update_data["county"] = new_county
            if new_sector:
                update_data["sector"] = new_sector
            if not args.dry_run:
                _safe_update(client, "reports", update_data, rid)
                time.sleep(_UPDATE_THROTTLE)
            local_updates += 1
        else:
            still_needs_county = current_county == "unknown" and not new_county
            still_needs_sector = current_sector == "political" and not new_sector
            if still_needs_county or still_needs_sector:
                needs_llm.append(report)

    print(f"Tier 1 (local): Updated {local_updates} reports.")
    print(f"Tier 2 needed:  {len(needs_llm)} reports remaining.")

    if skip_llm or not needs_llm:
        if args.dry_run:
            print("[dry-run] No writes were made.")
        print("Done.")
        return 0

    # ---- Tier 2: LLM classification ----
    engine_name = args.engine
    llm_client = None
    use_ollama = False

    if engine_name == "gemini":
        llm_client = _init_gemini()
        if llm_client is None:
            print("Gemini not available. Set GEMINI_API_KEY or use --engine ollama.")
            return 1
    elif engine_name == "ollama":
        llm_client = _init_ollama()
        if llm_client is None:
            print("Ollama not reachable. Start Ollama or use --engine gemini.")
            return 1
        use_ollama = True
    else:  # auto
        llm_client = _init_gemini()
        if llm_client is None:
            print("[auto] Gemini unavailable, trying Ollama...")
            llm_client = _init_ollama()
            if llm_client is None:
                print("No LLM available. Run with --skip-llm or start Ollama / set GEMINI_API_KEY.")
                return 1
            use_ollama = True

    engine_label = "Ollama" if use_ollama else "Gemini"
    print(f"Using {engine_label} for Tier 2.")

    llm_updates = 0
    total_batches = (len(needs_llm) + args.batch_size - 1) // args.batch_size

    for batch_idx in range(0, len(needs_llm), args.batch_size):
        batch = needs_llm[batch_idx : batch_idx + args.batch_size]
        batch_num = batch_idx // args.batch_size + 1
        print(f"  {engine_label} batch {batch_num}/{total_batches} ({len(batch)} texts)...")

        texts_for_llm = []
        for i, report in enumerate(batch):
            texts_for_llm.append({"i": i, "t": (report.get("text") or "")[:200]})

        if use_ollama:
            results = _call_ollama_batch(llm_client, texts_for_llm, workers=args.workers)
        else:
            results = _call_gemini_batch(llm_client, texts_for_llm)

        batch_ok = 0
        batch_fail = 0
        result_map = {r["i"]: r for r in results}
        for i, report in enumerate(batch):
            r = result_map.get(i)
            if not r or (not r.get("sector") and not r.get("county")):
                batch_fail += 1
                continue
            rid = report["id"]
            current_county = (report.get("county") or "unknown").strip()
            current_sector = (report.get("sector") or "political").strip()

            update_data: dict = {}
            if r["sector"]:
                update_data["gemini_sector"] = r["sector"]
                if current_sector == "political":
                    update_data["sector"] = r["sector"]
            if r["county"]:
                update_data["gemini_county"] = r["county"]
                if current_county == "unknown":
                    update_data["county"] = r["county"]

            if update_data and not args.dry_run:
                _safe_update(client, "reports", update_data, rid)
                time.sleep(_UPDATE_THROTTLE)
                llm_updates += 1
            batch_ok += 1

        print(f"    -> {batch_ok} ok, {batch_fail} failed")

        if batch_idx + args.batch_size < len(needs_llm):
            time.sleep(args.delay)

    print(f"Tier 2 ({engine_label}): Updated {llm_updates} reports.")
    if args.dry_run:
        print("[dry-run] No writes were made.")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
