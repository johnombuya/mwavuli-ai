"""
RSS/Atom feed fetcher for ingestion pipeline.

Fetches only allowlisted feeds, rate-limited and with polite User-Agent.
Outputs candidates: url, title, snippet, source_feed.
"""

import re
import time
from typing import List, Dict, Any

import feedparser

from app.ingestion.utils import normalise_url

# Max snippet length sent to verify API (same as API max_length for text)
SNIPPET_MAX_LEN = 5000


def _get_snippet(entry: Any) -> str:
    """Extract snippet from feed entry (description or content)."""
    summary = getattr(entry, "summary", "") or ""
    if summary:
        text = summary
    else:
        # Try content
        content = getattr(entry, "content", None)
        if content and isinstance(content, list) and content:
            text = getattr(content[0], "value", "") or ""
        else:
            text = getattr(entry, "description", "") or ""
    if not text:
        return ""
    # Strip HTML roughly
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())
    return text[:SNIPPET_MAX_LEN] if len(text) > SNIPPET_MAX_LEN else text


def fetch_feeds(
    feed_urls: List[str],
    user_agent: str,
    rate_limit_delay_seconds: float = 2.0,
    timeout_seconds: int = 10,
) -> List[Dict[str, str]]:
    """
    Fetch allowlisted RSS/Atom feeds and return candidate items.
    
    Args:
        feed_urls: List of feed URLs (allowlisted).
        user_agent: User-Agent for requests.
        rate_limit_delay_seconds: Delay between feeds.
        timeout_seconds: Request timeout per feed.
        
    Returns:
        List of dicts: url (canonical), title, snippet, source_feed.
    """
    candidates = []
    for feed_url in feed_urls:
        if not feed_url.strip():
            continue
        try:
            # feedparser uses urllib under the hood; we can pass a custom agent
            parsed = feedparser.parse(
                feed_url,
                request_headers={"User-Agent": user_agent},
                timeout=timeout_seconds,
            )
        except Exception as e:
            print(f"[ingestion] Feed error {feed_url}: {e}")
            continue
        if getattr(parsed, "bozo", False) and not getattr(parsed, "entries", None):
            print(f"[ingestion] Feed parse error (bozo) {feed_url}")
            continue
        entries = getattr(parsed, "entries", []) or []
        for entry in entries:
            link = getattr(entry, "link", "") or ""
            if not link:
                continue
            canonical = normalise_url(link)
            if not canonical:
                continue
            title = getattr(entry, "title", "") or ""
            snippet = _get_snippet(entry)
            candidates.append({
                "url": canonical,
                "title": title,
                "snippet": snippet,
                "source_feed": feed_url,
                "source_type": "rss",
            })
        time.sleep(rate_limit_delay_seconds)
    return candidates
