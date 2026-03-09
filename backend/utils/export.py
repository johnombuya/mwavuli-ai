"""
Data export utilities for Looker Studio integration.

This module provides functions to export report data in formats
compatible with Looker Studio and other analytics tools.
"""

import csv
import io
import json
import zipfile
from datetime import datetime
from typing import List, Dict, Optional, Any
from utils.db import _get_db
from firebase_admin import firestore
from utils import analytics


def _get_reports_collection():
    """Get reference to the reports collection."""
    db = _get_db()
    if db is None:
        return None
    return db.collection("artifacts").document("mwavuli").collection("public").document("data").collection("reports")


def _flatten_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten nested report structure for CSV export.
    
    Args:
        report: Report dictionary with nested fields
        
    Returns:
        Flattened dictionary suitable for CSV
    """
    flattened = {}
    
    # Basic fields
    flattened["id"] = report.get("id", "")
    flattened["text"] = report.get("text", "")
    flattened["risk_level"] = report.get("risk_level", "")
    flattened["language"] = report.get("language", "")
    flattened["county"] = report.get("county", "")
    flattened["region"] = report.get("region", "")
    flattened["is_urban"] = report.get("is_urban", False)
    
    # Timestamp fields
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
    
    # Temporal fields
    flattened["hour_of_day"] = report.get("hour_of_day", "")
    flattened["day_of_week"] = report.get("day_of_week", "")
    flattened["is_weekend"] = report.get("is_weekend", False)
    
    # Content analysis
    flattened["text_length"] = report.get("text_length", 0)
    flattened["word_count"] = report.get("word_count", 0)
    flattened["has_urls"] = report.get("has_urls", False)
    flattened["has_mentions"] = report.get("has_mentions", False)
    
    # Detection metadata
    flattened["detection_method"] = report.get("detection_method", "")
    flattened["confidence_score"] = report.get("confidence_score", 0.0)
    flattened["matched_keyword"] = report.get("matched_keyword", "")
    flattened["gemini_context_flag"] = report.get("gemini_context_flag", False)
    
    # Toxicity scores (flatten nested dict)
    scores = report.get("scores", {})
    if isinstance(scores, dict):
        flattened["toxicity"] = scores.get("toxicity", 0.0)
        flattened["severe_toxicity"] = scores.get("severe_toxicity", 0.0)
        flattened["obscene"] = scores.get("obscene", 0.0)
        flattened["threat"] = scores.get("threat", 0.0)
        flattened["insult"] = scores.get("insult", 0.0)
        flattened["identity_attack"] = scores.get("identity_attack", 0.0)
        # Calculate max toxicity
        score_values = [v for k, v in scores.items() 
                       if k not in ["error", "fallback"] and isinstance(v, (int, float))]
        flattened["max_toxicity"] = max(score_values) if score_values else 0.0
    else:
        flattened["toxicity"] = 0.0
        flattened["severe_toxicity"] = 0.0
        flattened["obscene"] = 0.0
        flattened["threat"] = 0.0
        flattened["insult"] = 0.0
        flattened["identity_attack"] = 0.0
        flattened["max_toxicity"] = 0.0
    
    # Anonymized sender hash
    flattened["sender_hash"] = "[REDACTED]"
    
    return flattened


def export_reports_to_csv(start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          fields: Optional[List[str]] = None) -> str:
    """
    Export reports to CSV format for Looker Studio.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        fields: List of fields to include (optional, includes all if None)
        
    Returns:
        CSV string
    """
    collection_ref = _get_reports_collection()
    if collection_ref is None:
        return ""
    
    try:
        # Build query
        query_ref = collection_ref
        if start_date:
            query_ref = query_ref.where("timestamp", ">=", start_date)
        if end_date:
            query_ref = query_ref.where("timestamp", "<=", end_date)
        
        query_ref = query_ref.order_by("timestamp", direction=firestore.Query.DESCENDING)
        
        # Fetch reports
        reports = []
        for doc in query_ref.stream():
            report = doc.to_dict()
            report["id"] = doc.id
            reports.append(report)
        
        if not reports:
            return ""
        
        # Flatten reports
        flattened_reports = [_flatten_report(r) for r in reports]
        
        # Determine fields
        if fields:
            # Use specified fields
            available_fields = set(flattened_reports[0].keys())
            export_fields = [f for f in fields if f in available_fields]
        else:
            # Use all fields
            export_fields = list(flattened_reports[0].keys())
        
        # Generate CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=export_fields)
        writer.writeheader()
        writer.writerows([{k: r.get(k, "") for k in export_fields} for r in flattened_reports])
        
        return output.getvalue()
    except Exception as e:
        print(f"Error exporting reports to CSV: {e}")
        return ""


def export_reports_to_json(start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           flatten: bool = False) -> List[Dict]:
    """
    Export reports to JSON format.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        flatten: Whether to flatten nested structures (default: False)
        
    Returns:
        List of report dictionaries
    """
    collection_ref = _get_reports_collection()
    if collection_ref is None:
        return []
    
    try:
        # Build query
        query_ref = collection_ref
        if start_date:
            query_ref = query_ref.where("timestamp", ">=", start_date)
        if end_date:
            query_ref = query_ref.where("timestamp", "<=", end_date)
        
        query_ref = query_ref.order_by("timestamp", direction=firestore.Query.DESCENDING)
        
        # Fetch reports
        reports = []
        for doc in query_ref.stream():
            report = doc.to_dict()
            report["id"] = doc.id
            
            # Convert datetime to ISO string for JSON serialization
            if "timestamp" in report and isinstance(report["timestamp"], datetime):
                report["timestamp"] = report["timestamp"].isoformat()
            
            if flatten:
                report = _flatten_report(report)
            
            reports.append(report)
        
        return reports
    except Exception as e:
        print(f"Error exporting reports to JSON: {e}")
        return []


def export_analytics_to_csv(analytics_type: str,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> str:
    """
    Export aggregated analytics to CSV format.
    
    Args:
        analytics_type: Type of analytics ("summary", "risk_distribution", etc.)
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        CSV string
    """
    try:
        # Get analytics data
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
            writer = csv.DictWriter(output, fieldnames=["county", "HIGH", "MEDIUM", "LOW", "total", 
                                                       "high_percentage", "medium_percentage", "low_percentage"])
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
        
        else:
            return ""
    except Exception as e:
        print(f"Error exporting analytics to CSV: {e}")
        return ""


def create_looker_studio_view(start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Create optimized data view for Looker Studio.
    
    This function creates a pre-aggregated view with common metrics
    that Looker Studio can use for faster visualization.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        Dictionary with pre-aggregated data
    """
    try:
        # Get summary stats
        summary = analytics.get_summary_stats(start_date, end_date)
        
        # Get risk distribution
        risk_dist = analytics.get_risk_level_distribution(start_date, end_date)
        
        # Get county analysis
        county_analysis = analytics.get_county_risk_analysis(None, start_date, end_date)
        
        # Get keyword trends (top 10)
        keyword_trends = analytics.get_keyword_trends(10, start_date, end_date)
        
        # Get toxicity trends
        toxicity_trends = analytics.get_toxicity_trends(30, start_date, end_date)
        
        # Get hourly patterns
        hourly_patterns = analytics.get_hourly_patterns(start_date, end_date)
        
        # Get daily patterns
        daily_patterns = analytics.get_daily_patterns(start_date, end_date)
        
        return {
            "summary": summary,
            "risk_distribution": risk_dist,
            "county_analysis": county_analysis,
            "keyword_trends": keyword_trends,
            "toxicity_trends": toxicity_trends,
            "hourly_patterns": hourly_patterns,
            "daily_patterns": daily_patterns,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Error creating Looker Studio view: {e}")
        return {}


def export_for_bigquery(start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> List[Dict]:
    """
    Format data for BigQuery export.
    
    This function formats reports in a way that's optimized for BigQuery
    import, with proper data types and nested structures preserved.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        List of formatted report dictionaries
    """
    collection_ref = _get_reports_collection()
    if collection_ref is None:
        return []
    
    try:
        # Build query
        query_ref = collection_ref
        if start_date:
            query_ref = query_ref.where("timestamp", ">=", start_date)
        if end_date:
            query_ref = query_ref.where("timestamp", "<=", end_date)
        
        query_ref = query_ref.order_by("timestamp", direction=firestore.Query.DESCENDING)
        
        # Fetch and format reports
        reports = []
        for doc in query_ref.stream():
            report = doc.to_dict()
            report["id"] = doc.id
            
            # Ensure timestamp is in proper format
            if "timestamp" in report and isinstance(report["timestamp"], datetime):
                report["timestamp"] = report["timestamp"].isoformat()
            
            # Ensure all nested structures are JSON-serializable
            if "scores" in report and isinstance(report["scores"], dict):
                # Keep scores as nested dict (BigQuery supports nested structures)
                pass
            
            reports.append(report)
        
        return reports
    except Exception as e:
        print(f"Error formatting data for BigQuery: {e}")
        return []


def export_report_pack(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> bytes:
    """
    Build a ZIP bundle containing reports.csv and summary.json for the date range.
    Suitable for one-click "report pack" export.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        csv_data = export_reports_to_csv(start_date, end_date, None)
        zf.writestr("reports.csv", csv_data or "no data")
        stats = analytics.get_summary_stats(start_date, end_date)
        zf.writestr("summary.json", json.dumps(stats, indent=2, default=str))
        zf.writestr("methodology.txt", "Mwavuli report pack. See https://github.com/niru-mwavuli for methodology.")
    buf.seek(0)
    return buf.read()
