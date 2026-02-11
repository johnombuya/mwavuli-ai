"""
Shared utilities for the ingestion pipeline (URL normalisation, etc.).
"""

from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


# Query params to strip for canonical URL (tracking, etc.)
STRIP_QUERY_PARAMS = frozenset(
    "utm_source utm_medium utm_campaign utm_term utm_content fbclid".split()
)


def normalise_url(url: str) -> str:
    """
    Normalise URL for deduplication: strip fragment and common tracking params.
    
    Args:
        url: Raw URL from feed or scraper
        
    Returns:
        Canonical URL (same article will get same string)
    """
    if not url or not url.strip():
        return ""
    parsed = urlparse(url.strip())
    # Drop fragment
    netloc = parsed.netloc or ""
    path = parsed.path or "/"
    # Filter query string
    if parsed.query:
        qs = parse_qs(parsed.query, keep_blank_values=False)
        filtered = {k: v for k, v in qs.items() if k.lower() not in STRIP_QUERY_PARAMS}
        query = urlencode(filtered, doseq=True)
    else:
        query = ""
    return urlunparse((parsed.scheme or "https", netloc, path, "", query, ""))
