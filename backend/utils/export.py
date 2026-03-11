"""
Data export utilities for Looker Studio integration.

This module provides functions to export report data in formats
compatible with Looker Studio and other analytics tools. All database
access goes through the ReportRepository abstraction.
"""

import csv
import io
import json
import zipfile
from datetime import datetime
from typing import List, Dict, Optional, Any

from utils.db import get_repository
from utils import analytics


def _flatten_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten nested report structure for CSV export."""
    flattened = {}

    flattened["id"] = report.get("id", "")
    flattened["text"] = report.get("text", "")
    flattened["risk_level"] = report.get("risk_level", "")
    flattened["language"] = report.get("language", "")
    flattened["county"] = report.get("county", "")
    flattened["region"] = report.get("region", "")
    flattened["is_urban"] = report.get("is_urban", False)

    timestamp = report.get("timestamp")
    if timestamp:
        if isinstance(timestamp, datetime):
            flattened["timestamp"] = timestamp.isoformat()
            flattened["date"] = timestamp.strftime("%Y-%m-%d")
            flattened["time"] = timestamp.strftime("%H:%M:%S")
        else:
            flattened["timestamp"] = str(timestamp)
            flattened["date"] = str(timestamp)[:10]
            flattened["time"] = str(timestamp)[11:19] if len(str(timestamp)) > 19 else ""
    else:
        flattened["timestamp"] = ""
        flattened["date"] = ""
        flattened["time"] = ""

    flattened["hour_of_day"] = report.get("hour_of_day", "")
    flattened["day_of_week"] = report.get("day_of_week", "")
    flattened["is_weekend"] = report.get("is_weekend", False)

    flattened["text_length"] = report.get("text_length", 0)
    flattened["word_count"] = report.get("word_count", 0)
    flattened["has_urls"] = report.get("has_urls", False)
    flattened["has_mentions"] = report.get("has_mentions", False)

    flattened["detection_method"] = report.get("detection_method", "")
    flattened["confidence_score"] = report.get("confidence_score", 0.0)
    flattened["matched_keyword"] = report.get("matched_keyword", "")
    flattened["gemini_context_flag"] = report.get("gemini_context_flag", False)

    scores = report.get("scores", {})
    if isinstance(scores, dict):
        flattened["toxicity"] = scores.get("toxicity", 0.0)
        flattened["severe_toxicity"] = scores.get("severe_toxicity", 0.0)
        flattened["obscene"] = scores.get("obscene", 0.0)
        flattened["threat"] = scores.get("threat", 0.0)
        flattened["insult"] = scores.get("insult", 0.0)
        flattened["identity_attack"] = scores.get("identity_attack", 0.0)
        score_values = [
            v for k, v in scores.items()
            if k not in ("error", "fallback") and isinstance(v, (int, float))
        ]
        flattened["max_toxicity"] = max(score_values) if score_values else 0.0
    else:
        for key in ("toxicity", "severe_toxicity", "obscene", "threat", "insult", "identity_attack", "max_toxicity"):
            flattened[key] = 0.0

    flattened["sender_hash"] = "[REDACTED]"
    return flattened


def export_reports_to_csv(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    fields: Optional[List[str]] = None,
) -> str:
    """Export reports to CSV format."""
    try:
        reports = get_repository().query_reports(
            start_date=start_date,
            end_date=end_date,
            order_by_timestamp="desc",
        )
        if not reports:
            return ""

        flattened_reports = [_flatten_report(r) for r in reports]

        if fields:
            available_fields = set(flattened_reports[0].keys())
            export_fields = [f for f in fields if f in available_fields]
        else:
            export_fields = list(flattened_reports[0].keys())

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=export_fields)
        writer.writeheader()
        writer.writerows([{k: r.get(k, "") for k in export_fields} for r in flattened_reports])
        return output.getvalue()
    except Exception as e:
        print(f"Error exporting reports to CSV: {e}")
        return ""


def export_reports_to_json(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    flatten: bool = False,
) -> List[Dict]:
    """Export reports to JSON format."""
    try:
        reports = get_repository().query_reports(
            start_date=start_date,
            end_date=end_date,
            order_by_timestamp="desc",
        )
        results = []
        for report in reports:
            if "timestamp" in report and isinstance(report["timestamp"], datetime):
                report["timestamp"] = report["timestamp"].isoformat()
            if flatten:
                report = _flatten_report(report)
            results.append(report)
        return results
    except Exception as e:
        print(f"Error exporting reports to JSON: {e}")
        return []


def export_analytics_to_csv(
    analytics_type: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> str:
    """Export aggregated analytics to CSV format."""
    try:
        if analytics_type == "risk_distribution":
            data = analytics.get_risk_level_distribution(start_date, end_date)
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["risk_level", "count"])
            for risk_level, count in data.items():
                writer.writerow([risk_level, count])
            return output.getvalue()

        elif analytics_type == "county_analysis":
            data = analytics.get_county_risk_analysis(None, start_date, end_date)
            if not data:
                return ""
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=["county", "HIGH", "MEDIUM", "LOW", "total",
                            "high_percentage", "medium_percentage", "low_percentage"],
            )
            writer.writeheader()
            for county, counts in data.items():
                writer.writerow({"county": county, **counts})
            return output.getvalue()

        elif analytics_type == "keyword_trends":
            data = analytics.get_keyword_trends(100, start_date, end_date)
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["keyword", "count"])
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()

        elif analytics_type == "toxicity_trends":
            data = analytics.get_toxicity_trends(30, start_date, end_date)
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["date", "avg_toxicity", "count"])
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()

        return ""
    except Exception as e:
        print(f"Error exporting analytics to CSV: {e}")
        return ""


def create_looker_studio_view(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Create optimized data view for Looker Studio."""
    try:
        return {
            "summary": analytics.get_summary_stats(start_date, end_date),
            "risk_distribution": analytics.get_risk_level_distribution(start_date, end_date),
            "county_analysis": analytics.get_county_risk_analysis(None, start_date, end_date),
            "keyword_trends": analytics.get_keyword_trends(10, start_date, end_date),
            "toxicity_trends": analytics.get_toxicity_trends(30, start_date, end_date),
            "hourly_patterns": analytics.get_hourly_patterns(start_date, end_date),
            "daily_patterns": analytics.get_daily_patterns(start_date, end_date),
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        print(f"Error creating Looker Studio view: {e}")
        return {}


def export_for_bigquery(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict]:
    """Format data for BigQuery export."""
    try:
        reports = get_repository().query_reports(
            start_date=start_date,
            end_date=end_date,
            order_by_timestamp="desc",
        )
        for report in reports:
            if "timestamp" in report and isinstance(report["timestamp"], datetime):
                report["timestamp"] = report["timestamp"].isoformat()
        return reports
    except Exception as e:
        print(f"Error formatting data for BigQuery: {e}")
        return []


def export_report_pack(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> bytes:
    """Build a ZIP bundle containing reports.csv and summary.json."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        csv_data = export_reports_to_csv(start_date, end_date, None)
        zf.writestr("reports.csv", csv_data or "no data")
        stats = analytics.get_summary_stats(start_date, end_date)
        zf.writestr("summary.json", json.dumps(stats, indent=2, default=str))
        zf.writestr(
            "methodology.txt",
            "Mwavuli report pack. See https://github.com/niru-mwavuli for methodology.",
        )
    buf.seek(0)
    return buf.read()
