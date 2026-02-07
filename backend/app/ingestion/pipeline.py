"""
Ingestion pipeline: fetch (RSS + scraper) -> dedupe -> filter -> verify -> save.

Runs the same analyzer as the API and writes reports with source_type, source_url,
created_by=system. Audit log written for each decision.
"""

import hashlib
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from utils import ingestion_config as config
from utils.db import (
    report_exists_by_source_url,
    report_exists_by_content_hash,
    save_report,
    write_ingestion_audit,
)
from app.ingestion.utils import normalise_url
from app.ingestion.feed_fetcher import fetch_feeds
from app.ingestion.scraper import fetch_seed_urls

# Max text length for verify (match API)
TEXT_MAX_LEN = 5000


def _text_for_verify(candidate: Dict[str, Any]) -> str:
    """Build text to send to analyzer (title + snippet, truncated)."""
    title = candidate.get("title") or ""
    snippet = candidate.get("snippet") or ""
    combined = (title + "\n\n" + snippet).strip() or snippet
    return combined[:TEXT_MAX_LEN] if len(combined) > TEXT_MAX_LEN else combined


def _content_hash(text: str) -> str:
    """SHA-256 of normalized text for content deduplication."""
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _matches_keywords(text: str, keywords: List[str]) -> bool:
    """True if text (case-insensitive) contains any keyword."""
    if not keywords:
        return True
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)


async def run_pipeline() -> Dict[str, int]:
    """
    Run one ingestion cycle: fetch, dedupe, filter, verify, save. Audit each step.
    
    Returns:
        Counts: fetched, duplicate_skipped, filter_skipped, verified, saved, failed.
    """
    counts = {
        "fetched": 0,
        "duplicate_skipped": 0,
        "filter_skipped": 0,
        "verified": 0,
        "saved": 0,
        "failed": 0,
    }
    if not config.is_ingestion_enabled():
        return counts

    job_id = config.get_job_id() or datetime.utcnow().strftime("%Y%m%d%H%M%S")
    rss_feeds = config.get_rss_feeds()
    scrape_domains = config.get_scrape_domains()
    scrape_seeds = config.get_scrape_seed_urls()
    keywords = config.get_election_keywords()
    user_agent = config.get_user_agent()
    rate_limit = config.get_rate_limit_req_per_min()

    # 1) Fetch
    candidates: List[Dict[str, Any]] = []
    if rss_feeds:
        rss_candidates = fetch_feeds(
            rss_feeds,
            user_agent=user_agent,
            rate_limit_delay_seconds=max(1.0, 60.0 / rate_limit) if rate_limit else 2.0,
        )
        candidates.extend(rss_candidates)
    if scrape_domains and scrape_seeds:
        allowed = {d.lower().split(":")[0] for d in scrape_domains if d}
        scrape_candidates = fetch_seed_urls(
            scrape_seeds,
            allowed_domains=allowed,
            user_agent=user_agent,
            rate_limit_req_per_min=rate_limit,
        )
        candidates.extend(scrape_candidates)

    counts["fetched"] = len(candidates)

    # 2) Dedupe by URL (and optionally content hash)
    to_verify: List[Dict[str, Any]] = []
    for c in candidates:
        url = normalise_url(c.get("url", "") or "")
        if not url:
            continue
        if report_exists_by_source_url(url):
            write_ingestion_audit("duplicate_skipped", job_id, c.get("source_type", ""), url, "duplicate")
            counts["duplicate_skipped"] += 1
            continue
        text = _text_for_verify(c)
        if not text.strip():
            continue
        content_hash = _content_hash(text)
        if report_exists_by_content_hash(content_hash):
            write_ingestion_audit("duplicate_skipped", job_id, c.get("source_type", ""), url, "content_duplicate")
            counts["duplicate_skipped"] += 1
            continue
        c["_content_hash"] = content_hash
        to_verify.append(c)

    # 3) Relevance filter
    if keywords:
        filtered = []
        for c in to_verify:
            text = _text_for_verify(c)
            if _matches_keywords(text, keywords):
                filtered.append(c)
            else:
                write_ingestion_audit("filter_skipped", job_id, c.get("source_type", ""), c.get("url", ""), "not relevant")
                counts["filter_skipped"] += 1
        to_verify = filtered

    # 4) Verify and save
    from models.text_analyzer import get_analyzer

    analyzer = get_analyzer()
    for c in to_verify:
        url = c.get("url", "")
        source_type = c.get("source_type", "rss")
        text = _text_for_verify(c)
        if not text.strip():
            continue
        try:
            result = await analyzer.analyze(text)
            counts["verified"] += 1
        except Exception as e:
            print(f"[ingestion] Verify error {url}: {e}")
            write_ingestion_audit("error", job_id, source_type, url, str(e))
            counts["failed"] += 1
            continue

        report_data = {
            "text": text,
            "risk_level": result.risk_level,
            "language": "auto-detect",
            "county": "unknown",
            "sender_id": "ingestion-rss" if source_type == "rss" else "ingestion-scraper",
            "scores": result.scores,
            "source_type": source_type,
            "source_url": url,
            "content_hash": c.get("_content_hash", ""),
            "created_by": "system",
            "ingestion_job_id": job_id,
        }
        if result.matched_keyword:
            report_data["matched_keyword"] = result.matched_keyword
        if result.gemini_context_flag:
            report_data["gemini_context_flag"] = True

        doc_id = save_report(report_data)
        if doc_id:
            write_ingestion_audit("verified", job_id, source_type, url, "", result.risk_level)
            counts["saved"] += 1
        else:
            write_ingestion_audit("save_failed", job_id, source_type, url, "save_report returned None")
            counts["failed"] += 1

    return counts
