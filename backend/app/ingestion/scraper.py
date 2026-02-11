"""
Allowlisted web scraper for ingestion pipeline.

Only fetches URLs whose host is in the allowlist. Respects robots.txt,
rate limits, and uses a circuit breaker per domain after repeated failures.
"""

import time
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
import trafilatura

from app.ingestion.utils import normalise_url

SNIPPET_MAX_LEN = 5000
CIRCUIT_BREAKER_FAILURES = 3
DEFAULT_TIMEOUT = 10


class CircuitBreaker:
    """Temporarily disable a domain after repeated failures."""

    def __init__(self, max_failures: int = CIRCUIT_BREAKER_FAILURES):
        self.max_failures = max_failures
        self._failures: Dict[str, int] = {}

    def record_failure(self, domain: str) -> None:
        self._failures[domain] = self._failures.get(domain, 0) + 1

    def is_open(self, domain: str) -> bool:
        return self._failures.get(domain, 0) >= self.max_failures

    def reset(self, domain: str) -> None:
        self._failures.pop(domain, None)


class RobotsCache:
    """Cache robots.txt per host for the run."""

    def __init__(self, user_agent: str, timeout: int = 5):
        self.user_agent = user_agent
        self.timeout = timeout
        self._parsers: Dict[str, Optional[RobotFileParser]] = {}

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        netloc = parsed.netloc or ""
        if not netloc:
            return False
        if netloc not in self._parsers:
            rp = RobotFileParser()
            scheme = parsed.scheme or "https"
            robots_url = f"{scheme}://{netloc}/robots.txt"
            try:
                rp.set_url(robots_url)
                rp.read()
                self._parsers[netloc] = rp
            except Exception as e:
                print(f"[ingestion] robots.txt error for {netloc}: {e}")
                self._parsers[netloc] = None
        rp = self._parsers[netloc]
        if rp is None:
            return True  # Allow if we couldn't fetch robots.txt (fail open for MVP)
        return rp.can_fetch(self.user_agent, url)


def _domain_allowed(url: str, allowed_domains: Set[str]) -> bool:
    parsed = urlparse(url)
    netloc = (parsed.netloc or "").lower()
    if not netloc:
        return False
    # Strip port for comparison
    domain = netloc.split(":")[0]
    return domain in allowed_domains


def fetch_url(
    url: str,
    allowed_domains: Set[str],
    user_agent: str,
    robots: RobotsCache,
    circuit_breaker: CircuitBreaker,
    timeout: int = DEFAULT_TIMEOUT,
    rate_limit_delay: float = 1.0,
) -> Optional[Dict[str, str]]:
    """
    Fetch a single URL if allowed and robots.txt permits. Extract main text.
    
    Returns:
        Dict with url (canonical), title, snippet, source_type="scraped", or None.
    """
    canonical = normalise_url(url)
    if not canonical:
        return None
    parsed = urlparse(canonical)
    domain = (parsed.netloc or "").lower().split(":")[0]
    if not domain or domain not in allowed_domains:
        return None
    if circuit_breaker.is_open(domain):
        return None
    if not robots.can_fetch(canonical):
        return None
    time.sleep(rate_limit_delay)
    try:
        resp = requests.get(
            canonical,
            headers={"User-Agent": user_agent},
            timeout=timeout,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[ingestion] Scrape error {canonical}: {e}")
        circuit_breaker.record_failure(domain)
        return None
    circuit_breaker.reset(domain)
    downloaded = resp.text
    if not downloaded:
        return None
    try:
        result = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        meta = trafilatura.extract_metadata(downloaded)
        title = (meta.title or "") if meta else ""
        text = result or ""
    except Exception:
        text = ""
        title = ""
    if not text and not title:
        return None
    snippet = (title + "\n\n" + text).strip()[:SNIPPET_MAX_LEN]
    return {
        "url": canonical,
        "title": title or "",
        "snippet": snippet,
        "source_type": "scraped",
    }


def fetch_seed_urls(
    seed_urls: List[str],
    allowed_domains: Set[str],
    user_agent: str,
    rate_limit_req_per_min: int = 30,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[Dict[str, str]]:
    """
    Fetch each seed URL if its domain is allowlisted. Respects robots.txt,
    rate limit, and circuit breaker.
    
    Args:
        seed_urls: URLs to fetch (must be in allowed_domains).
        allowed_domains: Set of allowed host names (no port).
        user_agent: User-Agent string.
        rate_limit_req_per_min: Max requests per minute (spread across domains).
        timeout: Request timeout.
        
    Returns:
        List of {url, title, snippet, source_type}.
    """
    delay = 60.0 / rate_limit_req_per_min if rate_limit_req_per_min else 1.0
    robots = RobotsCache(user_agent)
    circuit_breaker = CircuitBreaker()
    allowed = {d.lower().split(":")[0] for d in allowed_domains if d}
    results = []
    for url in seed_urls:
        item = fetch_url(
            url,
            allowed,
            user_agent,
            robots,
            circuit_breaker,
            timeout=timeout,
            rate_limit_delay=delay,
        )
        if item:
            results.append(item)
    return results
