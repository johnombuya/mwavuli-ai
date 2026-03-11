"""
Shared helper functions and constants for database providers.

These utilities are provider-agnostic and used by both FirebaseRepository
and SupabaseRepository for report enrichment before storage.
"""

import os
import re
import hashlib
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from dotenv import load_dotenv

from utils.redact import redact_pii

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")

_SENDER_HASH_SALT = os.getenv("SENDER_HASH_SALT", "")

_VALID_STATUSES = {"pending", "reviewed", "escalated"}

COUNTY_TO_REGION = {
    "Nairobi": "Nairobi",
    "Mombasa": "Coast",
    "Kisumu": "Nyanza",
    "Nakuru": "Rift Valley",
    "Eldoret": "Rift Valley",
    "Thika": "Central",
    "Malindi": "Coast",
    "Kitale": "Rift Valley",
    "Garissa": "North Eastern",
    "Kakamega": "Western",
    "Meru": "Eastern",
    "Nyeri": "Central",
    "Machakos": "Eastern",
    "Embu": "Eastern",
    "Kiambu": "Central",
    "Muranga": "Central",
    "Narok": "Rift Valley",
    "Bungoma": "Western",
    "Busia": "Western",
    "Homa Bay": "Nyanza",
    "Kisii": "Nyanza",
    "Migori": "Nyanza",
    "Siaya": "Nyanza",
    "Vihiga": "Western",
    "Bomet": "Rift Valley",
    "Kericho": "Rift Valley",
    "Laikipia": "Rift Valley",
    "Nandi": "Rift Valley",
    "Trans Nzoia": "Rift Valley",
    "Uasin Gishu": "Rift Valley",
    "West Pokot": "Rift Valley",
    "Baringo": "Rift Valley",
    "Elgeyo Marakwet": "Rift Valley",
    "Samburu": "Rift Valley",
    "Turkana": "Rift Valley",
    "Nyandarua": "Central",
    "Kirinyaga": "Central",
    "Nyamira": "Nyanza",
    "Kajiado": "Rift Valley",
    "Makueni": "Eastern",
    "Taita Taveta": "Coast",
    "Kwale": "Coast",
    "Kilifi": "Coast",
    "Lamu": "Coast",
    "Tana River": "Coast",
    "Wajir": "North Eastern",
    "Mandera": "North Eastern",
    "Marsabit": "Eastern",
    "Isiolo": "Eastern",
    "Tharaka Nithi": "Eastern",
    "Kitui": "Eastern",
}

URBAN_COUNTIES = {
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika",
    "Malindi", "Kitale", "Garissa", "Kakamega", "Meru", "Nyeri",
    "Machakos", "Embu", "Kiambu",
}


def anonymize_sender(sender_id: str) -> str:
    """Create a salted, anonymized hash of the sender ID for privacy."""
    salted = _SENDER_HASH_SALT + sender_id
    return hashlib.sha256(salted.encode()).hexdigest()[:16]


def normalize_text_for_hash(text: str) -> str:
    """
    Normalize text for stable content hashing/deduplication.
    Lowercases, collapses internal whitespace, strips leading/trailing whitespace.
    """
    if not text:
        return ""
    return " ".join(str(text).split()).lower()


def get_temporal_fields(timestamp: datetime) -> Dict[str, Any]:
    """Extract temporal fields from timestamp."""
    return {
        "hour_of_day": timestamp.hour,
        "day_of_week": timestamp.strftime("%A"),
        "is_weekend": timestamp.weekday() >= 5,
    }


_URL_PATTERN = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)
_MENTION_PATTERN = re.compile(r'[@#]\w+')


def get_content_analysis(text: str) -> Dict[str, Any]:
    """Analyze text content for metadata."""
    words = text.split()
    return {
        "text_length": len(text),
        "word_count": len(words),
        "has_urls": bool(_URL_PATTERN.search(text)),
        "has_mentions": bool(_MENTION_PATTERN.search(text)),
    }


def get_detection_method(data: dict) -> Dict[str, Any]:
    """Determine detection method and confidence score from report data."""
    matched_keyword = data.get("matched_keyword")
    gemini_flag = data.get("gemini_context_flag", False)
    scores = data.get("scores", {})

    if matched_keyword:
        detection_method = "lexicon"
        confidence_score = 1.0
    elif gemini_flag:
        detection_method = "gemini"
        confidence_score = 0.9
    elif scores and isinstance(scores, dict) and "toxicity" in scores:
        detection_method = "detoxify"
        score_values = [v for k, v in scores.items() if k not in ("error", "fallback")]
        confidence_score = max(score_values) if score_values else 0.5
    else:
        detection_method = "unknown"
        confidence_score = 0.0

    if matched_keyword and (gemini_flag or (scores and "toxicity" in scores)):
        detection_method = "combined"
        confidence_score = min(1.0, confidence_score + 0.1)

    return {
        "detection_method": detection_method,
        "confidence_score": confidence_score,
    }


def get_geographic_fields(county: str) -> Dict[str, Any]:
    """Derive geographic metadata from county."""
    county_normalized = county.strip()
    return {
        "region": COUNTY_TO_REGION.get(county_normalized, "Unknown"),
        "is_urban": county_normalized in URBAN_COUNTIES,
    }


def enrich_report(data: dict) -> dict:
    """
    Build a fully enriched report document from raw input data.

    Applies PII redaction, sender anonymization, temporal/content/detection/
    geographic enrichment, and deduplication hash computation. Returns the
    enriched dict ready for storage (provider-agnostic).
    """
    timestamp = data.get("timestamp")
    if not isinstance(timestamp, datetime):
        timestamp = datetime.utcnow()

    text_for_hash = data.get("text", "")
    normalized_text = normalize_text_for_hash(text_for_hash)
    content_hash = data.get("content_hash")
    if not content_hash and normalized_text:
        content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    report: Dict[str, Any] = {
        "text": redact_pii(data.get("text", "")),
        "risk_level": data.get("risk_level", "UNKNOWN"),
        "language": data.get("language", "unknown"),
        "county": data.get("county", "unknown"),
        "timestamp": timestamp,
        "sender_hash": anonymize_sender(data.get("sender_id", "anonymous")),
    }

    report.update(get_temporal_fields(timestamp))

    text = data.get("text", "")
    report.update(get_content_analysis(text))
    report.update(get_detection_method(data))

    county = data.get("county", "unknown")
    if county != "unknown":
        report.update(get_geographic_fields(county))
    else:
        report["region"] = "Unknown"
        report["is_urban"] = False

    optional_fields = [
        "scores", "matched_keyword", "gemini_context_flag",
        "source_type", "source_url", "created_by", "ingestion_job_id",
        "explanation", "explanation_details", "confidence_score",
        "kenyan_model_risk", "kenyan_model_score",
    ]
    for field in optional_fields:
        if field in data:
            report[field] = data[field]

    if content_hash:
        report["content_hash"] = content_hash

    if data.get("coordinated_campaign"):
        report["coordinated_campaign"] = True
    if data.get("recommended_action"):
        report["recommended_action"] = data["recommended_action"]

    report["sector"] = data.get("sector", "political")
    if data.get("org_id"):
        report["org_id"] = data["org_id"]
    report["status"] = data.get("status", "pending")

    return report


def build_aggregate_update(report: Dict[str, Any]) -> dict:
    """
    Compute the incremental aggregate update fields from a single report.

    Returns a dict describing what to increment in the daily aggregate doc.
    Used by both Firebase (transactional merge) and Supabase (JSONB update).
    """
    risk = report.get("risk_level", "UNKNOWN")
    matched_keyword = report.get("matched_keyword")
    county = report.get("county", "unknown")
    scores = report.get("scores") or {}
    status = (report.get("status") or "pending").lower()
    detection_method = report.get("detection_method", "unknown")
    has_urls = bool(report.get("has_urls"))
    has_mentions = bool(report.get("has_mentions"))

    toxicity_score = None
    if isinstance(scores, dict):
        vals = [
            v for k, v in scores.items()
            if k not in ("error", "fallback") and isinstance(v, (int, float))
        ]
        if vals:
            toxicity_score = float(max(vals))

    return {
        "risk": risk,
        "matched_keyword": matched_keyword,
        "county": county,
        "toxicity_score": toxicity_score,
        "status": status,
        "detection_method": detection_method,
        "has_urls": has_urls,
        "has_mentions": has_mentions,
    }


def default_aggregate_doc(date_str: str, sector: str, org_id: str) -> dict:
    """Return an empty aggregate document skeleton."""
    return {
        "date": date_str,
        "sector": sector,
        "org_id": org_id,
        "risk_counts": {},
        "keyword_counts": {},
        "county_counts": {},
        "toxicity": {"sum": 0.0, "count": 0},
        "status_counts": {},
        "detection_method_counts": {},
        "url_mention_counts": {
            "with_urls": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0, "total": 0},
            "without_urls": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0, "total": 0},
            "with_mentions": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0, "total": 0},
            "without_mentions": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0, "total": 0},
        },
    }


def apply_aggregate_increment(agg: dict, update: dict) -> None:
    """
    Mutate *agg* in-place by applying the incremental *update* produced
    by ``build_aggregate_update``.
    """
    risk = update["risk"]
    matched_keyword = update["matched_keyword"]
    county = update["county"]
    toxicity_score = update["toxicity_score"]
    status = update["status"]
    detection_method = update["detection_method"]
    has_urls = update["has_urls"]
    has_mentions = update["has_mentions"]

    rc = agg.setdefault("risk_counts", {})
    rc[risk] = int(rc.get(risk, 0)) + 1

    if matched_keyword:
        kc = agg.setdefault("keyword_counts", {})
        kc[matched_keyword] = int(kc.get(matched_keyword, 0)) + 1

    if county and county != "unknown":
        cc = agg.setdefault("county_counts", {})
        cc[county] = int(cc.get(county, 0)) + 1

    if toxicity_score is not None:
        tox = agg.setdefault("toxicity", {"sum": 0.0, "count": 0})
        tox["sum"] = float(tox.get("sum", 0.0)) + toxicity_score
        tox["count"] = int(tox.get("count", 0)) + 1

    sc = agg.setdefault("status_counts", {})
    sc[status] = int(sc.get(status, 0)) + 1

    dmc = agg.setdefault("detection_method_counts", {})
    row = dmc.get(detection_method)
    if not isinstance(row, dict):
        row = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0, "total": 0}
    row[risk] = int(row.get(risk, 0)) + 1
    row["total"] = int(row.get("total", 0)) + 1
    dmc[detection_method] = row

    umc = agg.setdefault("url_mention_counts", {})

    def _bump(key: str):
        dist = umc.get(key)
        if not isinstance(dist, dict):
            dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0, "total": 0}
        dist[risk] = int(dist.get(risk, 0)) + 1
        dist["total"] = int(dist.get("total", 0)) + 1
        umc[key] = dist

    _bump("with_urls" if has_urls else "without_urls")
    _bump("with_mentions" if has_mentions else "without_mentions")
