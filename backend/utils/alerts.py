"""
Early warning alerts: compare recent metrics to threshold and notify via webhook (or email).

Run from a scheduled job (cron) or script. On breach (e.g. HIGH risk count in last 24h
exceeds threshold), calls configured webhook with a JSON payload.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")

from utils import analytics


def get_alert_webhook_url() -> Optional[str]:
    url = (os.getenv("ALERT_WEBHOOK_URL") or "").strip()
    return url or None


def get_alert_high_risk_threshold() -> int:
    try:
        return max(0, int(os.getenv("ALERT_HIGH_RISK_THRESHOLD", "10")))
    except ValueError:
        return 10


def check_and_fire_alert(
    window_hours: int = 24,
    webhook_url: Optional[str] = None,
    high_risk_threshold: Optional[int] = None,
    sector: Optional[str] = None,
    cross_sector: bool = False,
) -> bool:
    """
    Check last ``window_hours`` for HIGH risk count.  If >= threshold, POST
    to webhook.

    Args:
        sector:       Filter by a single sector (e.g. ``"political"``).
        cross_sector: When True, check ALL sectors; if 2+ sectors each
                      exceed *half* the threshold in the same window, fire
                      a compound alert.
    """
    from utils.emergency_config import get_emergency_mode

    webhook_url = webhook_url or get_alert_webhook_url()
    base_threshold = (
        high_risk_threshold
        if high_risk_threshold is not None
        else get_alert_high_risk_threshold()
    )
    threshold = max(1, base_threshold // 2) if get_emergency_mode() else base_threshold
    if not webhook_url:
        return False

    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(hours=window_hours)

    if cross_sector:
        from collections import defaultdict
        sector_counts: dict[str, int] = defaultdict(int)
        for s in ("political", "health", "security", "fraud"):
            dist = analytics.get_risk_level_distribution(
                start_dt, end_dt, sector=s,
            )
            sector_counts[s] = dist.get("HIGH", 0)
        breached = {
            s: c for s, c in sector_counts.items()
            if c >= threshold // 2
        }
        if len(breached) < 2:
            return False
        payload = {
            "event": "cross_sector_compound_alert",
            "timestamp": end_dt.isoformat() + "Z",
            "window_hours": window_hours,
            "breached_sectors": breached,
            "threshold": threshold,
        }
    else:
        distribution = analytics.get_risk_level_distribution(
            start_dt, end_dt, sector=sector,
        )
        high_count = distribution.get("HIGH", 0)
        if high_count < threshold:
            return False
        payload = {
            "event": "high_risk_threshold_breach",
            "timestamp": end_dt.isoformat() + "Z",
            "window_hours": window_hours,
            "high_risk_count": high_count,
            "threshold": threshold,
            "distribution": distribution,
            "sector": sector or "all",
        }

    try:
        import urllib.request
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if 200 <= resp.getcode() < 300:
                print(f"[alerts] Webhook fired: {payload.get('event')}")
                return True
    except Exception as e:
        print(f"[alerts] Webhook error: {e}")
    return False
