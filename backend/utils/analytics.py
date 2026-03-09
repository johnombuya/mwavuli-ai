"""
Analytics utilities for Mwavuli report analysis.

This module provides functions for querying and aggregating report data
stored in Firestore for pattern discovery and trend analysis.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict

from utils.db import _get_db
from firebase_admin import firestore


def _get_reports_collection():
    """Get reference to the reports collection."""
    db = _get_db()
    if db is None:
        print("[analytics] DB is None - Firestore not connected")
        return None
    ref = db.collection("artifacts").document("mwavuli").collection("public").document("data").collection("reports")
    print("[analytics] Reports collection ref obtained (DB connected)")
    return ref


def _build_date_filter(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
):
    """
    Build Firestore query with date, sector, and org_id filtering.
    
    Returns:
        Tuple of (query_ref, has_filters)
    """
    collection_ref = _get_reports_collection()
    if collection_ref is None:
        return None, False
    
    query_ref = collection_ref
    
    if start_date:
        query_ref = query_ref.where("timestamp", ">=", start_date)
    
    if end_date:
        query_ref = query_ref.where("timestamp", "<=", end_date)

    if sector:
        query_ref = query_ref.where("sector", "==", sector)

    if org_id:
        query_ref = query_ref.where("org_id", "==", org_id)
    
    return query_ref, bool(start_date or end_date or sector or org_id)


def get_risk_level_distribution(start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None,
                                sector: Optional[str] = None,
                                org_id: Optional[str] = None) -> Dict[str, int]:
    """
    Get distribution of risk levels over time period.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        Dictionary with risk level counts: {"HIGH": 10, "MEDIUM": 5, "LOW": 20}
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    
    try:
        distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        
        for doc in query_ref.stream():
            data = doc.to_dict()
            risk_level = data.get("risk_level", "UNKNOWN")
            distribution[risk_level] = distribution.get(risk_level, 0) + 1
        
        return distribution
    except Exception as e:
        print(f"Error getting risk level distribution: {e}")
        return {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}


def get_county_risk_analysis(county: Optional[str] = None,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None,
                              sector: Optional[str] = None,
                              org_id: Optional[str] = None) -> Dict:
    """
    Analyze risk levels by county.
    
    Args:
        county: Filter by specific county (optional)
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        Dictionary with county-level risk analysis
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return {}
    
    try:
        if county:
            query_ref = query_ref.where("county", "==", county)
        
        county_data = defaultdict(lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0})
        
        for doc in query_ref.stream():
            data = doc.to_dict()
            county_name = data.get("county", "unknown")
            risk_level = data.get("risk_level", "UNKNOWN")
            
            county_data[county_name][risk_level] += 1
            county_data[county_name]["total"] += 1
        
        # Convert to regular dict and calculate percentages
        result = {}
        for county_name, counts in county_data.items():
            total = counts["total"]
            result[county_name] = {
                **counts,
                "high_percentage": (counts["HIGH"] / total * 100) if total > 0 else 0,
                "medium_percentage": (counts["MEDIUM"] / total * 100) if total > 0 else 0,
                "low_percentage": (counts["LOW"] / total * 100) if total > 0 else 0
            }
        
        return result
    except Exception as e:
        print(f"Error getting county risk analysis: {e}")
        return {}


def get_keyword_trends(limit: int = 20,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      sector: Optional[str] = None,
                      org_id: Optional[str] = None) -> List[Dict]:
    """
    Get most frequently matched keywords.
    
    Args:
        limit: Maximum number of keywords to return
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        List of dictionaries with keyword and count: [{"keyword": "madoadoa", "count": 15}, ...]
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return []
    
    try:
        keyword_counter = Counter()
        
        for doc in query_ref.stream():
            data = doc.to_dict()
            matched_keyword = data.get("matched_keyword")
            if matched_keyword:
                keyword_counter[matched_keyword] += 1
        
        # Convert to list of dicts
        result = [
            {"keyword": keyword, "count": count}
            for keyword, count in keyword_counter.most_common(limit)
        ]
        
        return result
    except Exception as e:
        print(f"Error getting keyword trends: {e}")
        return []


def get_toxicity_trends(days: int = 30,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        sector: Optional[str] = None,
                        org_id: Optional[str] = None) -> List[Dict]:
    """
    Get average toxicity scores over time.
    
    Args:
        days: Number of days to analyze (if dates not provided)
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        List of dictionaries with date and average toxicity: [{"date": "2024-01-01", "avg_toxicity": 0.65}, ...]
    """
    query_ref, has_filters = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return []
    
    try:
        if not has_filters:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
        
        # Group by date
        daily_scores = defaultdict(list)
        
        for doc in query_ref.stream():
            data = doc.to_dict()
            timestamp = data.get("timestamp")
            scores = data.get("scores", {})
            
            if timestamp and scores:
                # Get max toxicity score
                score_values = [v for k, v in scores.items() 
                              if k not in ["error", "fallback"] and isinstance(v, (int, float))]
                if score_values:
                    max_score = max(score_values)
                    # Extract date (YYYY-MM-DD)
                    date_str = timestamp.strftime("%Y-%m-%d") if isinstance(timestamp, datetime) else str(timestamp)[:10]
                    daily_scores[date_str].append(max_score)
        
        # Calculate averages
        result = []
        for date_str in sorted(daily_scores.keys()):
            scores = daily_scores[date_str]
            avg_toxicity = sum(scores) / len(scores) if scores else 0
            result.append({
                "date": date_str,
                "avg_toxicity": round(avg_toxicity, 3),
                "count": len(scores)
            })
        
        return result
    except Exception as e:
        print(f"Error getting toxicity trends: {e}")
        return []


def get_hourly_patterns(start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       sector: Optional[str] = None,
                       org_id: Optional[str] = None) -> Dict:
    """
    Analyze when high-risk content is most common by hour.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        Dictionary with hourly risk distribution: {"0": {"HIGH": 5, "MEDIUM": 3, ...}, ...}
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return {}
    
    try:
        hourly_data = defaultdict(lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0})
        
        for doc in query_ref.stream():
            data = doc.to_dict()
            hour = data.get("hour_of_day")
            risk_level = data.get("risk_level", "UNKNOWN")
            
            if hour is not None:
                hour_str = str(hour)
                hourly_data[hour_str][risk_level] += 1
                hourly_data[hour_str]["total"] += 1
        
        # Convert to regular dict
        result = dict(hourly_data)
        
        # Add percentages
        for hour_str, counts in result.items():
            total = counts["total"]
            if total > 0:
                result[hour_str]["high_percentage"] = (counts["HIGH"] / total * 100)
                result[hour_str]["medium_percentage"] = (counts["MEDIUM"] / total * 100)
                result[hour_str]["low_percentage"] = (counts["LOW"] / total * 100)
        
        return result
    except Exception as e:
        print(f"Error getting hourly patterns: {e}")
        return {}


def get_daily_patterns(start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      sector: Optional[str] = None,
                      org_id: Optional[str] = None) -> Dict:
    """
    Analyze risk distribution by day of week.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        Dictionary with day-of-week risk distribution
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return {}
    
    try:
        daily_data = defaultdict(lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0})
        
        for doc in query_ref.stream():
            data = doc.to_dict()
            day_of_week = data.get("day_of_week")
            risk_level = data.get("risk_level", "UNKNOWN")
            
            if day_of_week:
                daily_data[day_of_week][risk_level] += 1
                daily_data[day_of_week]["total"] += 1
        
        # Convert to regular dict and add percentages
        result = {}
        for day, counts in daily_data.items():
            total = counts["total"]
            result[day] = {
                **counts,
                "high_percentage": (counts["HIGH"] / total * 100) if total > 0 else 0,
                "medium_percentage": (counts["MEDIUM"] / total * 100) if total > 0 else 0,
                "low_percentage": (counts["LOW"] / total * 100) if total > 0 else 0
            }
        
        return result
    except Exception as e:
        print(f"Error getting daily patterns: {e}")
        return {}


def get_gemini_vs_lexicon_comparison(start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None,
                                    sector: Optional[str] = None,
                                    org_id: Optional[str] = None) -> Dict:
    """
    Compare Gemini-detected vs lexicon-detected high-risk content.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        Dictionary with comparison statistics
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return {}
    
    try:
        stats = {
            "lexicon_detected": 0,
            "gemini_detected": 0,
            "both_detected": 0,
            "neither_detected": 0,
            "total": 0
        }
        
        for doc in query_ref.stream():
            data = doc.to_dict()
            matched_keyword = data.get("matched_keyword")
            gemini_flag = data.get("gemini_context_flag", False)
            risk_level = data.get("risk_level", "UNKNOWN")
            
            # Only count HIGH risk for this comparison
            if risk_level == "HIGH":
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
        
        # Calculate percentages
        if stats["total"] > 0:
            stats["lexicon_percentage"] = (stats["lexicon_detected"] / stats["total"] * 100)
            stats["gemini_percentage"] = (stats["gemini_detected"] / stats["total"] * 100)
            stats["both_percentage"] = (stats["both_detected"] / stats["total"] * 100)
            stats["neither_percentage"] = (stats["neither_detected"] / stats["total"] * 100)
        
        return stats
    except Exception as e:
        print(f"Error getting Gemini vs lexicon comparison: {e}")
        return {}


def get_geographic_heatmap(start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          sector: Optional[str] = None,
                          org_id: Optional[str] = None) -> Dict:
    """
    Get county-level risk aggregation for heatmap visualization.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        Dictionary with county-level risk data
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return {}
    
    try:
        county_data = defaultdict(lambda: {
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "total": 0,
            "avg_toxicity": []
        })
        
        for doc in query_ref.stream():
            data = doc.to_dict()
            county = data.get("county", "unknown")
            risk_level = data.get("risk_level", "UNKNOWN")
            scores = data.get("scores", {})
            
            county_data[county][risk_level] += 1
            county_data[county]["total"] += 1
            
            # Collect toxicity scores
            if scores:
                score_values = [v for k, v in scores.items() 
                              if k not in ["error", "fallback"] and isinstance(v, (int, float))]
                if score_values:
                    county_data[county]["avg_toxicity"].append(max(score_values))
        
        # Calculate averages and risk score
        result = {}
        for county, data in county_data.items():
            total = data["total"]
            avg_tox = sum(data["avg_toxicity"]) / len(data["avg_toxicity"]) if data["avg_toxicity"] else 0
            
            # Calculate risk score (weighted: HIGH=3, MEDIUM=2, LOW=1)
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
                "high_percentage": (data["HIGH"] / total * 100) if total > 0 else 0
            }
        
        return result
    except Exception as e:
        print(f"Error getting geographic heatmap: {e}")
        return {}


def get_summary_stats(start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None,
                     sector: Optional[str] = None,
                     org_id: Optional[str] = None) -> Dict:
    """
    Get overall statistics summary.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        Dictionary with summary statistics
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        print("[analytics] get_summary_stats: query_ref is None, returning zeros")
        return {
            "total_reports": 0,
            "risk_distribution": {},
            "avg_toxicity": 0,
            "top_keywords": [],
            "top_counties": [],
            "date_range": {"start": None, "end": None},
        }
    
    try:
        total = 0
        risk_dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        toxicity_scores = []
        keyword_counter = Counter()
        county_counter = Counter()
        
        for doc in query_ref.stream():
            if total == 0:
                print(f"[analytics] get_summary_stats: first report doc id = {doc.id}")
            data = doc.to_dict()
            total += 1
            
            risk_level = data.get("risk_level", "UNKNOWN")
            risk_dist[risk_level] = risk_dist.get(risk_level, 0) + 1
            
            # Collect toxicity scores
            scores = data.get("scores", {})
            if scores:
                score_values = [v for k, v in scores.items() 
                              if k not in ["error", "fallback"] and isinstance(v, (int, float))]
                if score_values:
                    toxicity_scores.append(max(score_values))
            
            # Count keywords
            matched_keyword = data.get("matched_keyword")
            if matched_keyword:
                keyword_counter[matched_keyword] += 1
            
            # Count counties
            county = data.get("county", "unknown")
            if county != "unknown":
                county_counter[county] += 1
        
        print(f"[analytics] get_summary_stats: total reports in query = {total}")
        avg_toxicity = sum(toxicity_scores) / len(toxicity_scores) if toxicity_scores else 0
        
        return {
            "total_reports": total,
            "risk_distribution": risk_dist,
            "avg_toxicity": round(avg_toxicity, 3),
            "top_keywords": [
                {"keyword": k, "count": v} 
                for k, v in keyword_counter.most_common(5)
            ],
            "top_counties": [
                {"county": k, "count": v} 
                for k, v in county_counter.most_common(5)
            ],
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            }
        }
    except Exception as e:
        print(f"Error getting summary stats: {e}")
        return {
            "total_reports": 0,
            "risk_distribution": {},
            "avg_toxicity": 0,
            "top_keywords": [],
            "top_counties": [],
            "date_range": {"start": None, "end": None},
        }


def get_anomalies(start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None,
                 threshold: float = 2.0,
                 sector: Optional[str] = None,
                 org_id: Optional[str] = None) -> List[Dict]:
    """
    Detect unusual spikes or patterns in reports.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        threshold: Standard deviation multiplier for anomaly detection
        
    Returns:
        List of detected anomalies
    """
    query_ref, has_filters = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return []


def get_top_tokens(limit: int = 20,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   risk_levels: Optional[List[str]] = None,
                   min_length: int = 4,
                   sector: Optional[str] = None,
                   org_id: Optional[str] = None) -> List[Dict]:
    """
    Get most frequent tokens from high-risk reports.

    This is a heuristic text-based trend separate from lexicon keywords.
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return []

    try:
        token_counter = Counter()
        risk_set = set(risk_levels or ["HIGH"])

        for doc in query_ref.stream():
            data = doc.to_dict()
            if data.get("risk_level") not in risk_set:
                continue
            text = str(data.get("text", "")).lower()
            if not text:
                continue
            # Simple tokenization: split on whitespace and strip punctuation
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
    
    try:
        # Group by date
        daily_counts = defaultdict(int)
        
        for doc in query_ref.stream():
            data = doc.to_dict()
            timestamp = data.get("timestamp")
            if timestamp:
                date_str = timestamp.strftime("%Y-%m-%d") if isinstance(timestamp, datetime) else str(timestamp)[:10]
                daily_counts[date_str] += 1
        
        if not daily_counts:
            return []
        
        # Calculate statistics
        counts = list(daily_counts.values())
        mean = sum(counts) / len(counts)
        variance = sum((x - mean) ** 2 for x in counts) / len(counts)
        std_dev = variance ** 0.5
        
        # Find anomalies
        anomalies = []
        for date_str, count in daily_counts.items():
            if abs(count - mean) > (threshold * std_dev):
                anomalies.append({
                    "date": date_str,
                    "count": count,
                    "expected": round(mean, 1),
                    "deviation": round(abs(count - mean) / std_dev, 2) if std_dev > 0 else 0
                })
        
        # Sort by deviation
        anomalies.sort(key=lambda x: x["deviation"], reverse=True)
        
        return anomalies
    except Exception as e:
        print(f"Error detecting anomalies: {e}")
        return []


def get_detection_method_risk_matrix(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict:
    """
    Aggregate counts by detection_method and risk_level.
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return {}

    try:
        matrix: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0, "total": 0}
        )

        for doc in query_ref.stream():
            data = doc.to_dict()
            method = data.get("detection_method", "unknown")
            risk = data.get("risk_level", "UNKNOWN")
            row = matrix[method]
            row[risk] = row.get(risk, 0) + 1
            row["total"] += 1

        return dict(matrix)
    except Exception as e:
        print(f"Error getting detection method risk matrix: {e}")
        return {}


def get_confidence_histogram(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    bucket_size: float = 0.1,
    sector: Optional[str] = None,
    org_id: Optional[str] = None,
) -> List[Dict]:
    """
    Build histogram of confidence_score across reports.
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return []

    try:
        buckets: Dict[str, int] = Counter()

        for doc in query_ref.stream():
            data = doc.to_dict()
            score = data.get("confidence_score")
            if not isinstance(score, (int, float)):
                continue
            # Clamp to [0, 1]
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
    """
    Compare risk distributions for reports with/without URLs and mentions.
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return {}

    try:
        def empty_dist() -> Dict[str, int]:
            return {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0, "total": 0}

        stats = {
            "with_urls": empty_dist(),
            "without_urls": empty_dist(),
            "with_mentions": empty_dist(),
            "without_mentions": empty_dist(),
        }

        for doc in query_ref.stream():
            data = doc.to_dict()
            risk = data.get("risk_level", "UNKNOWN")
            has_urls = bool(data.get("has_urls"))
            has_mentions = bool(data.get("has_mentions"))

            url_key = "with_urls" if has_urls else "without_urls"
            ment_key = "with_mentions" if has_mentions else "without_mentions"

            for key in (url_key, ment_key):
                dist = stats[key]
                dist[risk] = dist.get(risk, 0) + 1
                dist["total"] += 1

        return stats
    except Exception as e:
        print(f"Error getting URL/mention risk stats: {e}")
        return {}


def get_keyword_baseline(keyword: str, days: int = 30) -> float:
    """Return average daily count of *keyword* over the last *days* days."""
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days)
    query_ref, _ = _build_date_filter(start_dt, end_dt)
    if query_ref is None:
        return 0.0
    try:
        count = 0
        for doc in query_ref.stream():
            if doc.to_dict().get("matched_keyword") == keyword:
                count += 1
        return count / max(days, 1)
    except Exception:
        return 0.0


def get_coordinated_campaigns(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict]:
    """Return reports flagged as coordinated campaigns."""
    query_ref, _ = _build_date_filter(start_date, end_date)
    if query_ref is None:
        return []
    try:
        results = []
        for doc in query_ref.stream():
            data = doc.to_dict()
            if data.get("coordinated_campaign"):
                results.append({"id": doc.id, **data})
        return results
    except Exception as e:
        print(f"Error getting coordinated campaigns: {e}")
        return []


def get_national_risk_level(
    window_hours: int = 24,
    high_threshold_pct: float = 15.0,
    medium_threshold_pct: float = 30.0,
) -> Dict:
    """
    Compute a traffic-light national risk indicator.

    Returns ``{"level": "RED"|"AMBER"|"GREEN", "high_pct": float, ...}``.
    """
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
    """
    Count reports by moderation status.
    """
    query_ref, _ = _build_date_filter(start_date, end_date, sector=sector, org_id=org_id)
    if query_ref is None:
        return {}

    try:
        counts: Dict[str, int] = Counter()

        for doc in query_ref.stream():
            data = doc.to_dict()
            status = (data.get("status") or "pending").lower()
            counts[status] += 1

        total = sum(counts.values())
        return {
            "counts": dict(counts),
            "total": total,
        }
    except Exception as e:
        print(f"Error getting status counts: {e}")
        return {}