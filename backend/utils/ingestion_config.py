"""
Ingestion configuration for Project Mwavuli.

Loads web ingestion settings from environment. Only allowlisted feeds and
domains are ever used; INGESTION_ENABLED acts as a kill switch.
"""

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")


def _split_strip(s: str) -> List[str]:
    """Split by comma and strip each item; exclude empty strings."""
    if not s or not s.strip():
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def is_ingestion_enabled() -> bool:
    """True if web ingestion is enabled (kill switch)."""
    return os.getenv("INGESTION_ENABLED", "false").lower() in ("true", "1", "yes")


def get_rss_feeds() -> List[str]:
    """Allowlisted RSS/Atom feed URLs (comma-separated in env)."""
    return _split_strip(os.getenv("INGESTION_RSS_FEEDS", ""))


def get_scrape_domains() -> List[str]:
    """Allowlisted domains for scraping (comma-separated in env)."""
    return _split_strip(os.getenv("INGESTION_SCRAPE_DOMAINS", ""))


def get_scrape_seed_urls() -> List[str]:
    """Optional seed URLs for scraper (must be in INGESTION_SCRAPE_DOMAINS)."""
    return _split_strip(os.getenv("INGESTION_SCRAPE_SEED_URLS", ""))


def get_rate_limit_req_per_min() -> int:
    """Max requests per minute across all sources (polite default)."""
    try:
        return max(1, int(os.getenv("INGESTION_RATE_LIMIT_REQ_PER_MIN", "30")))
    except ValueError:
        return 30


def get_user_agent() -> str:
    """User-Agent string for fetchers (identifiable for site owners)."""
    return os.getenv(
        "INGESTION_USER_AGENT",
        "MwavuliElectionMonitor/1.0 (+https://github.com/niru-mwavuli)"
    )


def get_election_keywords() -> List[str]:
    """Optional keywords for relevance filter; empty = no filter."""
    return _split_strip(os.getenv("INGESTION_ELECTION_KEYWORDS", ""))


def get_job_id() -> str:
    """Optional run identifier for audit (e.g. timestamp)."""
    return os.getenv("INGESTION_JOB_ID", "")


def is_ingestion_admin_enabled() -> bool:
    """True if ingestion status admin endpoint is enabled."""
    return os.getenv("INGESTION_ADMIN_ENABLED", "false").lower() in ("true", "1", "yes")
