#!/usr/bin/env python3
"""
Run early-warning alert check: if HIGH risk count in last 24h exceeds threshold, fire webhook.

Use from backend directory:
  python scripts/run_alerts.py

Schedule with cron (e.g. every hour):
  0 * * * * cd /path/to/backend && python scripts/run_alerts.py

Requires ALERT_WEBHOOK_URL and optional ALERT_HIGH_RISK_THRESHOLD in .env.
"""

import os
import sys

_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)
os.chdir(_backend)

from utils.alerts import check_and_fire_alert

if __name__ == "__main__":
    fired = check_and_fire_alert(window_hours=24)
    print("[alerts] Alert fired" if fired else "[alerts] No alert (below threshold or no webhook)")
