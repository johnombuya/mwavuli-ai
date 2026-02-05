"""
Seed dummy reports into Firestore for testing analytics dashboards.

Usage (from backend/ directory):
    python scripts/seed_dummy_reports.py [--preset minimal|default|large] [--count N] [--generator NAME ...] [--dry-run]

Requires: .env with FIREBASE_SERVICE_ACCOUNT_PATH (and optionally FIREBASE_DATABASE_ID).

Future-proof: To add more dummy data later:
  1. Define a function that returns a list of report dicts (same shape as build_report()).
  2. Register it in REPORT_GENERATORS below.
  3. Run with: python scripts/seed_dummy_reports.py --generator your_generator_name
  Or call your generator from main() and extend the reports list.
"""

import os
import re
import sys
import random
import hashlib
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable

# Ensure backend root is on path and load .env from backend
BACKEND_ROOT = Path(__file__).resolve().parent.parent
os.chdir(BACKEND_ROOT)
sys.path.insert(0, str(BACKEND_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_ROOT / ".env")  # backend/.env only
except ImportError:
    pass  # Optional for --dry-run; use venv + pip install -r requirements.txt for Firestore write

# firebase_admin is imported only when writing to Firestore (get_firestore_collection)


# ---------- Data config (extend these for more variety) ----------

COUNTY_TO_REGION: Dict[str, str] = {
    "Nairobi": "Nairobi", "Mombasa": "Coast", "Kisumu": "Nyanza", "Nakuru": "Rift Valley",
    "Kiambu": "Central", "Meru": "Eastern", "Nyeri": "Central", "Machakos": "Eastern",
    "Kakamega": "Western", "Garissa": "North Eastern", "Kisii": "Nyanza", "Bungoma": "Western",
    "Kericho": "Rift Valley", "Uasin Gishu": "Rift Valley", "Kilifi": "Coast",
    "Embu": "Eastern", "Migori": "Nyanza", "Siaya": "Nyanza", "Kajiado": "Rift Valley",
}
URBAN_COUNTIES = frozenset({
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Garissa", "Kakamega", "Meru", "Nyeri",
    "Machakos", "Kiambu", "Embu",
})

HIGH_RISK_KEYWORDS = [
    "madoadoa", "kama mende", "wageni", "wabara", "toeni", "songa mbele",
    "funga debe", "no raila no peace", "kwekwe", "wafukuze", "uthamaki",
]
MEDIUM_RISK_KEYWORDS = ["uchaguzi", "vita", "mapambano", "mwizi"]

SAMPLE_TEXTS_LOW = [
    "Hello, how are you today?",
    "The weather is nice in Nairobi.",
    "Please share the meeting link when ready.",
    "Thanks for the update on the project.",
    "Elections should be free and fair.",
]
SAMPLE_TEXTS_MEDIUM = [
    "The uchaguzi process must be transparent.",
    "Mapambano ya kisiasa zinaendelea.",
    "We need peace during the election period.",
]
SAMPLE_TEXTS_HIGH = [
    "Those madoadoa must leave this region.",
    "Wageni hawa wanachangia hasira.",
    "Toeni wote wabara hapa.",
    "No raila no peace in the streets.",
    "Funga debe and fix the results.",
]

# Presets: name -> default count for random generator
PRESETS: Dict[str, int] = {
    "minimal": 50,
    "default": 200,
    "large": 1000,
}


# ---------- Report building (same shape as utils.db save_report) ----------

def _anonymize_sender(sender_id: str) -> str:
    return hashlib.sha256(sender_id.encode()).hexdigest()[:16]


def _get_content_analysis(text: str) -> Dict[str, Any]:
    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F]{2}))+"
    )
    mention_pattern = re.compile(r"[@#]\w+")
    words = text.split()
    return {
        "text_length": len(text),
        "word_count": len(words),
        "has_urls": bool(url_pattern.search(text)),
        "has_mentions": bool(mention_pattern.search(text)),
    }


def build_report(
    timestamp: datetime,
    risk_level: str,
    county: str,
    text: str,
    sender_id: str,
    matched_keyword: Optional[str] = None,
    gemini_context_flag: bool = False,
    scores: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a single report document matching Firestore shape used by analytics."""
    region = COUNTY_TO_REGION.get(county, "Unknown")
    is_urban = county in URBAN_COUNTIES
    report: Dict[str, Any] = {
        "text": text,
        "risk_level": risk_level,
        "language": "en",
        "county": county,
        "timestamp": timestamp,
        "sender_hash": _anonymize_sender(sender_id),
        "hour_of_day": timestamp.hour,
        "day_of_week": timestamp.strftime("%A"),
        "is_weekend": timestamp.weekday() >= 5,
        "region": region,
        "is_urban": is_urban,
    }
    report.update(_get_content_analysis(text))

    if matched_keyword:
        report["matched_keyword"] = matched_keyword
        report["detection_method"] = "lexicon"
        report["confidence_score"] = 1.0
    elif gemini_context_flag:
        report["gemini_context_flag"] = True
        report["detection_method"] = "gemini"
        report["confidence_score"] = 0.9
    elif scores:
        report["scores"] = scores
        report["detection_method"] = "detoxify"
        score_vals = [v for v in scores.values() if isinstance(v, (int, float))]
        report["confidence_score"] = max(score_vals, default=0.5)
    else:
        report["detection_method"] = "unknown"
        report["confidence_score"] = 0.0

    if matched_keyword and (gemini_context_flag or scores):
        report["detection_method"] = "combined"
        report["confidence_score"] = min(1.0, report["confidence_score"] + 0.1)

    return report


# ---------- Report generators (add new ones here for more dummy data) ----------

def generate_random_reports(count: int) -> List[Dict[str, Any]]:
    """Generate `count` reports with random timestamps, counties, and risk mix over last 30 days."""
    counties = list(COUNTY_TO_REGION.keys())
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    reports: List[Dict[str, Any]] = []

    for i in range(count):
        ts = start + timedelta(
            seconds=random.randint(0, max(0, int((end - start).total_seconds()))),
        )
        county = random.choice(counties)
        sender_id = f"seed_user_{i % 50}_{random.randint(1000, 9999)}"

        r = random.random()
        if r < 0.25:
            risk_level = "HIGH"
            kw = random.choice(HIGH_RISK_KEYWORDS)
            t = random.choice(SAMPLE_TEXTS_HIGH)
            text = t.replace("madoadoa", kw) if "madoadoa" in t else t
            scores = {"toxicity": round(0.7 + random.random() * 0.25, 3)}
            report = build_report(
                ts, risk_level, county, text, sender_id,
                matched_keyword=kw, scores=scores,
            )
        elif r < 0.60:
            risk_level = "MEDIUM"
            text = random.choice(SAMPLE_TEXTS_MEDIUM)
            matched_keyword = random.choice(MEDIUM_RISK_KEYWORDS) if random.random() < 0.3 else None
            scores = {"toxicity": round(0.4 + random.random() * 0.3, 3)}
            report = build_report(
                ts, risk_level, county, text, sender_id,
                matched_keyword=matched_keyword, scores=scores,
            )
        else:
            risk_level = "LOW" if random.random() < 0.95 else "UNKNOWN"
            text = random.choice(SAMPLE_TEXTS_LOW)
            scores = {"toxicity": round(random.random() * 0.35, 3)} if random.random() < 0.5 else None
            report = build_report(ts, risk_level, county, text, sender_id, scores=scores)

        reports.append(report)

    return reports


def generate_election_week_spike() -> List[Dict[str, Any]]:
    """Fixed scenario: burst of HIGH-risk reports in a short window (e.g. for testing spikes)."""
    base = datetime.now(timezone.utc) - timedelta(days=14)
    counties = ["Nairobi", "Mombasa", "Kisumu", "Nakuru"]
    reports: List[Dict[str, Any]] = []
    for h in range(24):
        for _ in range(3):
            ts = base + timedelta(hours=h)
            county = random.choice(counties)
            kw = random.choice(HIGH_RISK_KEYWORDS)
            t = random.choice(SAMPLE_TEXTS_HIGH)
            text = t.replace("madoadoa", kw) if "madoadoa" in t else t
            reports.append(
                build_report(
                    ts, "HIGH", county, text, f"spike_user_{h}",
                    matched_keyword=kw, scores={"toxicity": round(0.8 + random.random() * 0.2, 3)},
                )
            )
    return reports


def generate_fixed_minimal() -> List[Dict[str, Any]]:
    """Small fixed set for reproducible tests (summary, risk dist, keywords, heatmap)."""
    base = datetime.now(timezone.utc) - timedelta(days=7)
    return [
        build_report(base, "HIGH", "Nairobi", "Those madoadoa must leave.", "u1",
                     matched_keyword="madoadoa", scores={"toxicity": 0.92}),
        build_report(base + timedelta(hours=2), "MEDIUM", "Mombasa", "Uchaguzi must be fair.", "u2",
                     matched_keyword="uchaguzi", scores={"toxicity": 0.55}),
        build_report(base + timedelta(days=1), "LOW", "Kisumu", "Hello, weather is nice.", "u3",
                     scores={"toxicity": 0.12}),
        build_report(base + timedelta(days=2), "HIGH", "Nakuru", "Wageni hawa wanachangia hasira.", "u4",
                     matched_keyword="wageni", scores={"toxicity": 0.88}),
        build_report(base + timedelta(days=3), "MEDIUM", "Kiambu", "Mapambano ya kisiasa.", "u5",
                     scores={"toxicity": 0.48}),
        build_report(base + timedelta(days=4), "LOW", "Meru", "Thanks for the update.", "u6", scores=None),
    ]


# Registry: add new generators here to expose them via --generator NAME
REPORT_GENERATORS: Dict[str, Callable[..., List[Dict[str, Any]]]] = {
    "random": generate_random_reports,
    "election_spike": generate_election_week_spike,
    "fixed_minimal": generate_fixed_minimal,
}


# ---------- Firestore ----------

def get_firestore_collection():
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        raise SystemExit("Install dependencies: pip install firebase-admin python-dotenv (or use venv + pip install -r requirements.txt)")
    raw_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH") or "firebase-service-account.json"
    path = Path(raw_path)
    if not path.is_absolute():
        path = (BACKEND_ROOT / path).resolve()
    service_account_path = str(path)
    if not path.exists():
        fallback = BACKEND_ROOT / "firebase-service-account.json"
        if fallback.exists():
            service_account_path = str(fallback)
        else:
            raise SystemExit(f"Credentials file not found: {service_account_path}")
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(service_account_path)
        database_id = os.getenv("FIREBASE_DATABASE_ID") or None
        firebase_admin.initialize_app(cred)
        db = firestore.client(database_id=database_id) if database_id else firestore.client()
    else:
        database_id = os.getenv("FIREBASE_DATABASE_ID")
        db = firestore.client(database_id=database_id) if database_id else firestore.client()
    return db.collection("artifacts").document("mwavuli").collection("public").document("data").collection("reports")


# ---------- CLI ----------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed dummy reports into Firestore for analytics testing.",
        epilog="Generators: " + ", ".join(REPORT_GENERATORS.keys()),
    )
    parser.add_argument(
        "--preset", choices=list(PRESETS), default="default",
        help="Preset for random count (minimal=50, default=200, large=1000)",
    )
    parser.add_argument("--count", type=int, default=None, help="Override count for 'random' generator")
    parser.add_argument(
        "--generator", action="append", dest="generators", metavar="NAME",
        help="Use only these generators (default: random with preset count). Can be repeated.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate reports but do not write to Firestore")
    args = parser.parse_args()

    reports: List[Dict[str, Any]] = []

    if args.generators:
        for name in args.generators:
            if name not in REPORT_GENERATORS:
                print(f"Unknown generator: {name}. Choose from: {list(REPORT_GENERATORS.keys())}")
                sys.exit(1)
            gen = REPORT_GENERATORS[name]
            if name == "random":
                count = args.count if args.count is not None else PRESETS[args.preset]
                batch = gen(count)
            else:
                batch = gen()
            reports.extend(batch)
            print(f"  {name}: {len(batch)} reports")
    else:
        count = args.count if args.count is not None else PRESETS[args.preset]
        reports = generate_random_reports(count)
        print(f"Generated {len(reports)} reports (preset={args.preset}, count={count}).")

    if not reports:
        print("No reports to write.")
        return

    print(f"Total reports: {len(reports)}")
    if args.dry_run:
        print("Dry run: not writing to Firestore.")
        return

    coll = get_firestore_collection()
    for i, report in enumerate(reports):
        coll.add(report)
        if (i + 1) % 50 == 0:
            print(f"  Written {i + 1}/{len(reports)}")
    print(f"Done. Written {len(reports)} reports to Firestore.")


if __name__ == "__main__":
    main()
