"""
Analytics utilities for Mwavuli report analysis.

This module provides functions for querying and aggregating report data
for pattern discovery and trend analysis. All database access goes
through the ReportRepository abstraction.
"""

import json as _json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import Counter, defaultdict

from utils.db import get_repository


def _ensure_dict(val: Any, default: Optional[dict] = None) -> dict:
    """Safely coerce *val* to a dict, handling double-serialized JSON strings."""
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = _json.loads(val)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            pass
    return default if default is not None else {}


def _iter_aggregates(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    sector: Optional[str],
    org_id: Optional[str],
) -> List[Dict]:
    """Yield aggregate documents for each day in [start_date, end_date]."""
    if not start_date or not end_date:
        return []
    return get_repository().get_aggregate_docs(start_date, end_date, sector, org_id)


def _query_raw_reports(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
    **kwargs,
) -> List[dict]:
    """Convenience wrapper around the repository's query_reports."""
    return get_repository().query_reports(
        start_date=start_date,
        end_date=end_date,
        sector=sector,
        org_id=org_id,
        **kwargs,
    )


def get_risk_level_distribution(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict[str, int]:
    """Get distribution of risk levels over time period (reads from aggregates)."""
    if not start_date or not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
    try:
        distribution: Dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        for agg in _iter_aggregates(start_date, end_date, sector, org_id):
            rc = _ensure_dict(agg.get("risk_counts"))
            for level, count in rc.items():
                distribution[level] = distribution.get(level, 0) + int(count)
        return distribution
    except Exception as e:
        print(f"Error getting risk level distribution from aggregates: {e}")
        return {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}


def get_county_risk_analysis(
    county: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict:
    """Analyze risk levels by county (scans raw reports)."""
    try:
        reports = _query_raw_reports(
            start_date, end_date, sector=sector, org_id=org_id, county=county,
        )
        county_data = defaultdict(lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0})
        for data in reports:
            county_name = data.get("county", "unknown")
            risk_level = data.get("risk_level", "UNKNOWN")
            county_data[county_name][risk_level] += 1
            county_data[county_name]["total"] += 1

        result = {}
        for county_name, counts in county_data.items():
            total = counts["total"]
            result[county_name] = {
                **counts,
                "high_percentage": (counts["HIGH"] / total * 100) if total > 0 else 0,
                "medium_percentage": (counts["MEDIUM"] / total * 100) if total > 0 else 0,
                "low_percentage": (counts["LOW"] / total * 100) if total > 0 else 0,
            }
        return result
    except Exception as e:
        print(f"Error getting county risk analysis: {e}")
        return {}


def get_keyword_trends(
    limit: int = 20,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> List[Dict]:
    """Get most frequently matched keywords using daily aggregates."""
    if not start_date or not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
    try:
        keyword_counter: Counter = Counter()
        for agg in _iter_aggregates(start_date, end_date, sector, org_id):
            kw = _ensure_dict(agg.get("keyword_counts"))
            for keyword, count in kw.items():
                keyword_counter[keyword] += int(count)
        return [
            {"keyword": keyword, "count": count}
            for keyword, count in keyword_counter.most_common(limit)
        ]
    except Exception as e:
        print(f"Error getting keyword trends from aggregates: {e}")
        return []


def get_toxicity_trends(
    days: int = 30,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> List[Dict]:
    """Get average toxicity scores over time using daily aggregates."""
    if not (start_date or end_date or sector or org_id):
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
    elif not (start_date and end_date):
        end_date = end_date or datetime.utcnow()
        start_date = start_date or (end_date - timedelta(days=days))

    try:
        results: List[Dict] = []
        for agg in _iter_aggregates(start_date, end_date, sector, org_id):
            date_str = agg.get("date")
            if not date_str:
                continue
            tox = _ensure_dict(agg.get("toxicity"))
            total_count = int(tox.get("count", 0))
            total_sum = float(tox.get("sum", 0.0))
            if total_count > 0:
                results.append({
                    "date": date_str,
                    "avg_toxicity": round(total_sum / total_count, 3),
                    "count": total_count,
                })
        results.sort(key=lambda x: x["date"])
        return results
    except Exception as e:
        print(f"Error getting toxicity trends from aggregates: {e}")
        return []


def get_hourly_patterns(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict:
    """Analyze when high-risk content is most common by hour (scans raw reports)."""
    try:
        reports = _query_raw_reports(start_date, end_date, sector=sector, org_id=org_id)
        hourly_data = defaultdict(lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0})
        for data in reports:
            hour = data.get("hour_of_day")
            risk_level = data.get("risk_level", "UNKNOWN")
            if hour is not None:
                hour_str = str(hour)
                hourly_data[hour_str][risk_level] += 1
                hourly_data[hour_str]["total"] += 1

        result = dict(hourly_data)
        for hour_str, counts in result.items():
            total = counts["total"]
            if total > 0:
                result[hour_str]["high_percentage"] = counts["HIGH"] / total * 100
                result[hour_str]["medium_percentage"] = counts["MEDIUM"] / total * 100
                result[hour_str]["low_percentage"] = counts["LOW"] / total * 100
        return result
    except Exception as e:
        print(f"Error getting hourly patterns: {e}")
        return {}


def get_daily_patterns(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict:
    """Analyze risk distribution by day of week (scans raw reports)."""
    try:
        reports = _query_raw_reports(start_date, end_date, sector=sector, org_id=org_id)
        daily_data = defaultdict(lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0})
        for data in reports:
            day_of_week = data.get("day_of_week")
            risk_level = data.get("risk_level", "UNKNOWN")
            if day_of_week:
                daily_data[day_of_week][risk_level] += 1
                daily_data[day_of_week]["total"] += 1

        result = {}
        for day, counts in daily_data.items():
            total = counts["total"]
            result[day] = {
                **counts,
                "high_percentage": (counts["HIGH"] / total * 100) if total > 0 else 0,
                "medium_percentage": (counts["MEDIUM"] / total * 100) if total > 0 else 0,
                "low_percentage": (counts["LOW"] / total * 100) if total > 0 else 0,
            }
        return result
    except Exception as e:
        print(f"Error getting daily patterns: {e}")
        return {}


def get_gemini_vs_lexicon_comparison(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict:
    """Compare Gemini-detected vs lexicon-detected high-risk content (raw scan)."""
    try:
        reports = _query_raw_reports(start_date, end_date, sector=sector, org_id=org_id)
        stats = {
            "lexicon_detected": 0, "gemini_detected": 0,
            "both_detected": 0, "neither_detected": 0, "total": 0,
        }
        for data in reports:
            if data.get("risk_level") != "HIGH":
                continue
            matched_keyword = data.get("matched_keyword")
            gemini_flag = data.get("gemini_context_flag", False)
            stats["total"] += 1
            has_lexicon = bool(matched_keyword)
            has_gemini = gemini_flag
            if has_lexicon and has_gemini:
                stats["both_detected"] += 1
            elif has_lexicon:
                stats["lexicon_detected"] += 1
            elif has_gemini:
                stats["gemini_detected"] += 1
            else:
                stats["neither_detected"] += 1

        if stats["total"] > 0:
            stats["lexicon_percentage"] = stats["lexicon_detected"] / stats["total"] * 100
            stats["gemini_percentage"] = stats["gemini_detected"] / stats["total"] * 100
            stats["both_percentage"] = stats["both_detected"] / stats["total"] * 100
            stats["neither_percentage"] = stats["neither_detected"] / stats["total"] * 100
        return stats
    except Exception as e:
        print(f"Error getting Gemini vs lexicon comparison: {e}")
        return {}


def get_geographic_heatmap(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict:
    """Get county-level risk aggregation for heatmap visualization (raw scan)."""
    try:
        reports = _query_raw_reports(start_date, end_date, sector=sector, org_id=org_id)
        county_data = defaultdict(
            lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0, "avg_toxicity": []}
        )
        for data in reports:
            county = data.get("county", "unknown")
            risk_level = data.get("risk_level", "UNKNOWN")
            scores = data.get("scores", {})
            county_data[county][risk_level] += 1
            county_data[county]["total"] += 1
            if scores:
                score_values = [
                    v for k, v in scores.items()
                    if k not in ("error", "fallback") and isinstance(v, (int, float))
                ]
                if score_values:
                    county_data[county]["avg_toxicity"].append(max(score_values))

        result = {}
        for county, data in county_data.items():
            total = data["total"]
            avg_tox = (
                sum(data["avg_toxicity"]) / len(data["avg_toxicity"])
                if data["avg_toxicity"] else 0
            )
            risk_score = (
                (data["HIGH"] * 3 + data["MEDIUM"] * 2 + data["LOW"] * 1) / total
                if total > 0 else 0
            )
            result[county] = {
                "HIGH": data["HIGH"],
                "MEDIUM": data["MEDIUM"],
                "LOW": data["LOW"],
                "total": total,
                "avg_toxicity": round(avg_tox, 3),
                "risk_score": round(risk_score, 2),
                "high_percentage": (data["HIGH"] / total * 100) if total > 0 else 0,
            }
        return result
    except Exception as e:
        print(f"Error getting geographic heatmap: {e}")
        return {}


def get_summary_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict:
    """Get overall statistics summary using daily aggregates."""
    if not start_date or not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
    try:
        total_reports = 0
        risk_dist: Dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        toxicity_sum = 0.0
        toxicity_count = 0
        keyword_counter: Counter = Counter()
        county_counter: Counter = Counter()

        for agg in _iter_aggregates(start_date, end_date, sector, org_id):
            rc = _ensure_dict(agg.get("risk_counts"))
            day_total = sum(int(v) for v in rc.values())
            total_reports += day_total
            for level, count in rc.items():
                risk_dist[level] = risk_dist.get(level, 0) + int(count)
            tox = _ensure_dict(agg.get("toxicity"))
            toxicity_sum += float(tox.get("sum", 0.0))
            toxicity_count += int(tox.get("count", 0))
            kw = _ensure_dict(agg.get("keyword_counts"))
            for k, v in kw.items():
                keyword_counter[k] += int(v)
            cc = _ensure_dict(agg.get("county_counts"))
            for c, v in cc.items():
                county_counter[c] += int(v)

        avg_toxicity = toxicity_sum / toxicity_count if toxicity_count > 0 else 0.0

        return {
            "total_reports": total_reports,
            "risk_distribution": risk_dist,
            "avg_toxicity": round(avg_toxicity, 3),
            "top_keywords": [
                {"keyword": k, "count": v} for k, v in keyword_counter.most_common(5)
            ],
            "top_counties": [
                {"county": k, "count": v} for k, v in county_counter.most_common(5)
            ],
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
        }
    except Exception as e:
        print(f"Error getting summary stats from aggregates: {e}")
        return {
            "total_reports": 0, "risk_distribution": {},
            "avg_toxicity": 0, "top_keywords": [], "top_counties": [],
            "date_range": {"start": None, "end": None},
        }


def get_anomalies(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    threshold: float = 2.0,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> List[Dict]:
    """Detect unusual spikes or patterns in reports (raw scan)."""
    try:
        reports = _query_raw_reports(start_date, end_date, sector=sector, org_id=org_id)
        daily_counts = defaultdict(int)
        for data in reports:
            timestamp = data.get("timestamp")
            if timestamp:
                date_str = (
                    timestamp.strftime("%Y-%m-%d")
                    if isinstance(timestamp, datetime)
                    else str(timestamp)[:10]
                )
                daily_counts[date_str] += 1

        if not daily_counts:
            return []

        counts = list(daily_counts.values())
        mean = sum(counts) / len(counts)
        variance = sum((x - mean) ** 2 for x in counts) / len(counts)
        std_dev = variance ** 0.5

        anomalies = []
        for date_str, count in daily_counts.items():
            if abs(count - mean) > (threshold * std_dev):
                anomalies.append({
                    "date": date_str,
                    "count": count,
                    "expected": round(mean, 1),
                    "deviation": round(abs(count - mean) / std_dev, 2) if std_dev > 0 else 0,
                })
        anomalies.sort(key=lambda x: x["deviation"], reverse=True)
        return anomalies
    except Exception as e:
        print(f"Error detecting anomalies: {e}")
        return []


def get_top_tokens(
    limit: int = 20,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    risk_levels: Optional[List[str]] = None,
    min_length: int = 4,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> List[Dict]:
    """Get most frequent tokens from high-risk reports (raw scan)."""
    try:
        reports = _query_raw_reports(start_date, end_date, sector=sector, org_id=org_id)
        token_counter = Counter()
        risk_set = set(risk_levels or ["HIGH"])

        for data in reports:
            if data.get("risk_level") not in risk_set:
                continue
            text = str(data.get("text", "")).lower()
            if not text:
                continue
            for raw in text.split():
                token = "".join(ch for ch in raw if ch.isalnum() or ch in {"@", "#"})
                if not token or token.startswith("http"):
                    continue
                if len(token) < min_length and not token.startswith(("@", "#")):
                    continue
                token_counter[token] += 1

        return [
            {"token": token, "count": count}
            for token, count in token_counter.most_common(limit)
        ]
    except Exception as e:
        print(f"Error getting top tokens: {e}")
        return []


def get_detection_method_risk_matrix(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict:
    """Aggregate counts by detection_method and risk_level using aggregates."""
    if not start_date or not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
    try:
        matrix: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0, "total": 0}
        )
        for agg in _iter_aggregates(start_date, end_date, sector, org_id):
            dmc = _ensure_dict(agg.get("detection_method_counts"))
            for method, raw_row in dmc.items():
                row = _ensure_dict(raw_row)
                target = matrix[method]
                for key in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"):
                    target[key] = target.get(key, 0) + int(row.get(key, 0))
                target["total"] = target.get("total", 0) + int(row.get("total", 0))
        return dict(matrix)
    except Exception as e:
        print(f"Error getting detection method risk matrix from aggregates: {e}")
        return {}


def get_confidence_histogram(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    bucket_size: float = 0.1,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> List[Dict]:
    """Build histogram of confidence_score across reports (raw scan)."""
    try:
        reports = _query_raw_reports(start_date, end_date, sector=sector, org_id=org_id)
        buckets: Dict[str, int] = Counter()
        for data in reports:
            score = data.get("confidence_score")
            if not isinstance(score, (int, float)):
                continue
            s = max(0.0, min(1.0, float(score)))
            bucket_index = int(s / bucket_size)
            if bucket_index >= int(1.0 / bucket_size):
                bucket_index = int(1.0 / bucket_size) - 1
            start = round(bucket_index * bucket_size, 2)
            end = round(start + bucket_size, 2)
            label = f"{start:.2f}-{end:.2f}"
            buckets[label] += 1
        return [
            {"bucket": label, "count": count}
            for label, count in sorted(buckets.items())
        ]
    except Exception as e:
        print(f"Error getting confidence histogram: {e}")
        return []


def get_url_mention_risk_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict:
    """Compare risk distributions for reports with/without URLs and mentions (aggregates)."""
    if not start_date or not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
    try:
        def empty_dist() -> Dict[str, int]:
            return {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0, "total": 0}

        stats = {
            "with_urls": empty_dist(), "without_urls": empty_dist(),
            "with_mentions": empty_dist(), "without_mentions": empty_dist(),
        }
        for agg in _iter_aggregates(start_date, end_date, sector, org_id):
            umc = _ensure_dict(agg.get("url_mention_counts"))
            for key in ("with_urls", "without_urls", "with_mentions", "without_mentions"):
                src = _ensure_dict(umc.get(key))
                dest = stats[key]
                for risk in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"):
                    dest[risk] = dest.get(risk, 0) + int(src.get(risk, 0))
                dest["total"] = dest.get("total", 0) + int(src.get("total", 0))
        return stats
    except Exception as e:
        print(f"Error getting URL/mention risk stats from aggregates: {e}")
        return {}


def get_keyword_baseline(keyword: str, days: int = 30) -> float:
    """Return average daily count of *keyword* over the last *days* days."""
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days)
    try:
        reports = _query_raw_reports(start_dt, end_dt)
        count = sum(1 for r in reports if r.get("matched_keyword") == keyword)
        return count / max(days, 1)
    except Exception:
        return 0.0


def get_coordinated_campaigns(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict]:
    """Return reports flagged as coordinated campaigns, grouped by narrative similarity."""
    try:
        reports = _query_raw_reports(start_date, end_date)
        flagged = [r for r in reports if r.get("coordinated_campaign")]
        if not flagged:
            return []

        # Group by sender and compute campaign-level stats
        sender_groups: Dict[str, List[Dict]] = defaultdict(list)
        for r in flagged:
            sender_groups[r.get("sender_hash", "unknown")].append(r)

        return {
            "campaigns": flagged,
            "unique_senders": len(sender_groups),
            "total_flagged": len(flagged),
            "risk_breakdown": dict(Counter(r.get("risk_level", "UNKNOWN") for r in flagged)),
        }
    except Exception as e:
        print(f"Error getting coordinated campaigns: {e}")
        return []


def get_national_risk_level(
    window_hours: int = 24,
    high_threshold_pct: float = 15.0,
    medium_threshold_pct: float = 30.0,
) -> Dict:
    """Compute a traffic-light national risk indicator using aggregates."""
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(hours=window_hours)
    dist = get_risk_level_distribution(start_dt, end_dt)
    total = sum(dist.values()) or 1
    high_pct = dist.get("HIGH", 0) / total * 100
    medium_pct = dist.get("MEDIUM", 0) / total * 100

    if high_pct >= high_threshold_pct:
        level = "RED"
    elif medium_pct >= medium_threshold_pct:
        level = "AMBER"
    else:
        level = "GREEN"

    return {
        "level": level,
        "high_pct": round(high_pct, 1),
        "medium_pct": round(medium_pct, 1),
        "total_reports": total,
        "window_hours": window_hours,
    }


def get_status_counts(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict:
    """Count reports by moderation status using daily aggregates."""
    if not start_date or not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
    try:
        counts: Counter = Counter()
        for agg in _iter_aggregates(start_date, end_date, sector, org_id):
            sc = _ensure_dict(agg.get("status_counts"))
            for status, value in sc.items():
                counts[status] += int(value)
        total = sum(counts.values())
        return {"counts": dict(counts), "total": total}
    except Exception as e:
        print(f"Error getting status counts from aggregates: {e}")
        return {}


# ── Topic Clusters & Lexicon Suggestions ─────────────────────────


def get_topic_clusters(active_only: bool = True) -> List[Dict]:
    """Return topic clusters from the report_clusters table."""
    try:
        repo = get_repository()
        client = getattr(repo, "_get_client", lambda: None)()
        if client is None:
            return []
        query = client.table("report_clusters").select("*")
        if active_only:
            query = query.eq("is_active", True)
        query = query.order("size", desc=True).limit(50)
        result = query.execute()
        return result.data or []
    except Exception as e:
        print(f"Error getting topic clusters: {e}")
        return []


def get_lexicon_suggestions(min_high_pct: float = 30.0, top_n: int = 20) -> List[Dict]:
    """
    Suggest new keywords by cross-referencing cluster keywords with the
    existing lexicon. Returns terms that appear frequently in HIGH-risk
    clusters but are NOT already in the lexicon.
    """
    try:
        from utils.lexicon import HIGH_RISK_KEYWORDS, MEDIUM_RISK_KEYWORDS

        existing = set(kw.lower() for kw in HIGH_RISK_KEYWORDS + MEDIUM_RISK_KEYWORDS)
        clusters = get_topic_clusters(active_only=True)
        if not clusters:
            return []

        suggestions: Counter = Counter()
        suggestion_context: Dict[str, Dict] = {}

        for cluster in clusters:
            risk = _ensure_dict(cluster.get("risk_breakdown"))
            total = sum(int(v) for v in risk.values()) or 1
            high_count = int(risk.get("HIGH", 0))
            high_pct = high_count / total * 100

            if high_pct < min_high_pct:
                continue

            keywords = cluster.get("top_keywords", [])
            if isinstance(keywords, str):
                try:
                    keywords = _json.loads(keywords)
                except (ValueError, TypeError):
                    keywords = []

            county_dist = _ensure_dict(cluster.get("county_distribution"))

            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in existing:
                    continue
                if len(kw_lower) < 3:
                    continue
                suggestions[kw_lower] += cluster.get("size", 1)
                if kw_lower not in suggestion_context:
                    suggestion_context[kw_lower] = {
                        "keyword": kw,
                        "cluster_count": 0,
                        "total_reports": 0,
                        "high_reports": 0,
                        "counties": Counter(),
                    }
                ctx = suggestion_context[kw_lower]
                ctx["cluster_count"] += 1
                ctx["total_reports"] += total
                ctx["high_reports"] += high_count
                for county, cnt in county_dist.items():
                    ctx["counties"][county] += int(cnt)

        results = []
        for kw, count in suggestions.most_common(top_n):
            ctx = suggestion_context[kw]
            results.append({
                "keyword": ctx["keyword"],
                "frequency": count,
                "cluster_count": ctx["cluster_count"],
                "total_reports": ctx["total_reports"],
                "high_reports": ctx["high_reports"],
                "top_counties": [
                    {"county": c, "count": n}
                    for c, n in ctx["counties"].most_common(3)
                ],
            })
        return results
    except Exception as e:
        print(f"Error getting lexicon suggestions: {e}")
        return []


# ---------------------------------------------------------------------------
# Executive summary (LLM-generated)
# ---------------------------------------------------------------------------

def generate_executive_summary() -> Dict:
    """Gather dashboard data and produce a plain-English intelligence brief.

    Uses the LLM_PROVIDER setting (gemini/ollama/auto) to generate the prose.
    Returns {"summary": str, "generated_at": str, "data": dict}.
    """
    import os
    import urllib.request
    from datetime import timezone

    risk = get_national_risk_level()
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(hours=24)
    stats = get_summary_stats(start_dt, end_dt)
    campaigns = get_coordinated_campaigns(start_dt, end_dt)
    clusters = get_topic_clusters(active_only=True)

    total = stats.get("total_reports", 0)
    risk_dist = stats.get("risk_distribution", {})
    top_counties = stats.get("top_counties", [])
    top_kw = stats.get("top_keywords", [])

    county_str = ", ".join(f"{c['county']} ({c['count']})" for c in top_counties[:5]) or "none"
    kw_str = ", ".join(f"{k['keyword']}" for k in top_kw[:5]) or "none"

    campaign_count = 0
    if isinstance(campaigns, dict):
        campaign_count = campaigns.get("total_flagged", len(campaigns.get("campaigns", [])))
    elif isinstance(campaigns, list):
        campaign_count = len(campaigns)

    cluster_summaries = []
    for c in clusters[:3]:
        kws = c.get("top_keywords", [])
        if isinstance(kws, str):
            try:
                kws = _json.loads(kws)
            except (ValueError, TypeError):
                kws = []
        label = ", ".join(kws[:3]) if kws else f"Cluster #{c.get('cluster_label', '?')}"
        cluster_summaries.append(f"{label} ({c.get('size', 0)} reports)")

    cluster_str = "; ".join(cluster_summaries) if cluster_summaries else "none detected"

    data_block = {
        "threat_level": risk.get("level", "GREEN"),
        "total_reports": total,
        "high_pct": risk.get("high_pct", 0),
        "medium_pct": risk.get("medium_pct", 0),
        "risk_distribution": risk_dist,
        "top_counties": county_str,
        "coordinated_campaigns": campaign_count,
        "narrative_clusters": cluster_str,
        "top_keywords": kw_str,
    }

    prompt = (
        "You are a security intelligence analyst writing for a government decision-maker. "
        "Write a 3-4 sentence executive brief. Be specific about counties, threats, and trends. "
        "Do not use bullet points. Use plain prose.\n\n"
        f"Data: {total} reports in the last 24 hours. Threat level: {risk.get('level', 'GREEN')}. "
        f"{risk.get('high_pct', 0)}% HIGH risk, {risk.get('medium_pct', 0)}% MEDIUM risk. "
        f"Risk breakdown: {risk_dist.get('HIGH', 0)} HIGH, {risk_dist.get('MEDIUM', 0)} MEDIUM, {risk_dist.get('LOW', 0)} LOW. "
        f"Top counties by activity: {county_str}. "
        f"Coordinated campaigns detected: {campaign_count}. "
        f"Active narrative clusters: {cluster_str}. "
        f"Top keywords: {kw_str}.\n\n"
        "Write the executive brief now."
    )

    summary = _call_llm_for_summary(prompt)

    if not summary:
        summary = (
            f"Threat level is {risk.get('level', 'GREEN')}. "
            f"{total} reports analyzed in the last 24 hours — "
            f"{risk_dist.get('HIGH', 0)} HIGH risk, {risk_dist.get('MEDIUM', 0)} MEDIUM, "
            f"{risk_dist.get('LOW', 0)} LOW. "
            f"Most active counties: {county_str}. "
            f"{campaign_count} coordinated campaign{'s' if campaign_count != 1 else ''} detected."
        )

    return {
        "summary": summary,
        "generated_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
        "data": data_block,
    }


def _call_llm_for_summary(prompt: str) -> Optional[str]:
    """Route an LLM call through LLM_PROVIDER for summary generation."""
    import os
    import urllib.request

    provider = os.getenv("LLM_PROVIDER", "auto").strip().lower()
    result = None

    if provider in ("gemini", "auto"):
        result = _call_gemini_summary(prompt)

    if result is None and provider in ("ollama", "auto"):
        result = _call_ollama_summary(prompt)

    return result


def _call_gemini_summary(prompt: str) -> Optional[str]:
    """Generate summary via Gemini."""
    import os
    try:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key or api_key == "your_gemini_api_key_here":
            return None
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"[exec-summary] Gemini error: {e}")
        return None


def _call_ollama_summary(prompt: str) -> Optional[str]:
    """Generate summary via Ollama."""
    import os
    import urllib.request

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    model = os.getenv("OLLAMA_MODEL", "llama3").strip()

    body = _json.dumps({
        "model": model,
        "prompt": prompt,
        "system": "You are a concise security intelligence analyst. Write in plain prose for decision-makers.",
        "stream": False,
    }).encode()

    try:
        req = urllib.request.Request(
            f"{base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = _json.loads(resp.read().decode())
            return data.get("response", "").strip() or None
    except Exception as e:
        print(f"[exec-summary] Ollama error: {e}")
        return None
