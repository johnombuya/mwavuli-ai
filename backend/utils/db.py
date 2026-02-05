"""
Firebase Firestore Database Utility for Project Mwavuli.

This module handles all database operations for logging verification reports.
Reports are stored anonymously for future pattern analysis and improving
the detection models.
"""

import os
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables from backend/.env only
_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")

# Firebase initialization state
_db = None
_initialized = False


def _get_db():
    """
    Initialize and return the Firestore client.
    Uses lazy initialization to avoid issues during import.
    """
    global _db, _initialized
    
    if _initialized:
        return _db
    
    try:
        # Get service account path from environment (relative to backend root if not absolute)
        raw_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        if not raw_path:
            raw_path = "firebase-service-account.json"
        path = Path(raw_path)
        if not path.is_absolute():
            path = (_backend_root / path).resolve()
        service_account_path = str(path)
        if not path.exists():
            _fallback = _backend_root / "firebase-service-account.json"
            if _fallback.exists():
                service_account_path = str(_fallback)
            else:
                print(f"Warning: Firebase credentials file not found at {service_account_path}")
                _initialized = True
                return None

        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(service_account_path)
        
        # Get custom database name from environment, default to None (uses default database)
        database_id = os.getenv("FIREBASE_DATABASE_ID", None)
        
        # Initialize Firebase app
        firebase_admin.initialize_app(cred)
        
        # Connect to Firestore with custom database if specified
        if database_id:
            _db = firestore.client(database_id=database_id)
            print(f"Firebase Firestore initialized successfully with database: {database_id}")
        else:
            _db = firestore.client()
            print("Firebase Firestore initialized successfully with default database.")
        
        _initialized = True
        return _db
        
    except Exception as e:
        print(f"Warning: Failed to initialize Firebase: {e}")
        _initialized = True
        return None


def _anonymize_sender(sender_id: str) -> str:
    """
    Create an anonymized hash of the sender ID for privacy.
    
    Args:
        sender_id: The original sender identifier
        
    Returns:
        A SHA-256 hash of the sender ID
    """
    return hashlib.sha256(sender_id.encode()).hexdigest()[:16]


# Kenyan counties mapped to regions
COUNTY_TO_REGION = {
    "Nairobi": "Nairobi",
    "Mombasa": "Coast",
    "Kisumu": "Nyanza",
    "Nakuru": "Rift Valley",
    "Eldoret": "Rift Valley",
    "Thika": "Central",
    "Malindi": "Coast",
    "Kitale": "Rift Valley",
    "Garissa": "North Eastern",
    "Kakamega": "Western",
    "Meru": "Eastern",
    "Nyeri": "Central",
    "Machakos": "Eastern",
    "Embu": "Eastern",
    "Kiambu": "Central",
    "Muranga": "Central",
    "Narok": "Rift Valley",
    "Bungoma": "Western",
    "Busia": "Western",
    "Homa Bay": "Nyanza",
    "Kisii": "Nyanza",
    "Migori": "Nyanza",
    "Siaya": "Nyanza",
    "Vihiga": "Western",
    "Bomet": "Rift Valley",
    "Kericho": "Rift Valley",
    "Laikipia": "Rift Valley",
    "Nandi": "Rift Valley",
    "Trans Nzoia": "Rift Valley",
    "Uasin Gishu": "Rift Valley",
    "West Pokot": "Rift Valley",
    "Baringo": "Rift Valley",
    "Elgeyo Marakwet": "Rift Valley",
    "Samburu": "Rift Valley",
    "Turkana": "Rift Valley",
    "Nyandarua": "Central",
    "Kirinyaga": "Central",
    "Nyamira": "Nyanza",
    "Kajiado": "Rift Valley",
    "Makueni": "Eastern",
    "Taita Taveta": "Coast",
    "Kwale": "Coast",
    "Kilifi": "Coast",
    "Lamu": "Coast",
    "Tana River": "Coast",
    "Wajir": "North Eastern",
    "Mandera": "North Eastern",
    "Marsabit": "Eastern",
    "Isiolo": "Eastern",
    "Meru": "Eastern",
    "Tharaka Nithi": "Eastern",
    "Kitui": "Eastern",
    "Machakos": "Eastern",
    "Makueni": "Eastern",
}

# Urban counties (major cities/towns)
URBAN_COUNTIES = {
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika",
    "Malindi", "Kitale", "Garissa", "Kakamega", "Meru", "Nyeri",
    "Machakos", "Embu", "Kiambu"
}


def _get_temporal_fields(timestamp: datetime) -> Dict[str, any]:
    """
    Extract temporal fields from timestamp.
    
    Args:
        timestamp: The datetime object
        
    Returns:
        Dictionary with hour_of_day, day_of_week, is_weekend
    """
    return {
        "hour_of_day": timestamp.hour,
        "day_of_week": timestamp.strftime("%A"),
        "is_weekend": timestamp.weekday() >= 5  # Saturday = 5, Sunday = 6
    }


def _get_content_analysis(text: str) -> Dict[str, any]:
    """
    Analyze text content for metadata.
    
    Args:
        text: The text to analyze
        
    Returns:
        Dictionary with text_length, word_count, has_urls, has_mentions
    """
    # URL pattern
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    # Mention pattern (@username or #hashtag)
    mention_pattern = re.compile(r'[@#]\w+')
    
    words = text.split()
    
    return {
        "text_length": len(text),
        "word_count": len(words),
        "has_urls": bool(url_pattern.search(text)),
        "has_mentions": bool(mention_pattern.search(text))
    }


def _get_detection_method(data: dict) -> Dict[str, any]:
    """
    Determine detection method and confidence score.
    
    Args:
        data: Report data dictionary
        
    Returns:
        Dictionary with detection_method and confidence_score
    """
    matched_keyword = data.get("matched_keyword")
    gemini_flag = data.get("gemini_context_flag", False)
    scores = data.get("scores", {})
    
    # Determine detection method
    if matched_keyword:
        detection_method = "lexicon"
        confidence_score = 1.0  # High confidence for lexicon matches
    elif gemini_flag:
        detection_method = "gemini"
        confidence_score = 0.9  # High confidence for Gemini detection
    elif scores and isinstance(scores, dict) and "toxicity" in scores:
        detection_method = "detoxify"
        # Use max toxicity score as confidence
        score_values = [v for k, v in scores.items() if k not in ["error", "fallback"]]
        confidence_score = max(score_values) if score_values else 0.5
    else:
        detection_method = "unknown"
        confidence_score = 0.0
    
    # If multiple methods detected, mark as combined
    if matched_keyword and (gemini_flag or (scores and "toxicity" in scores)):
        detection_method = "combined"
        confidence_score = min(1.0, confidence_score + 0.1)
    
    return {
        "detection_method": detection_method,
        "confidence_score": confidence_score
    }


def _get_geographic_fields(county: str) -> Dict[str, any]:
    """
    Derive geographic metadata from county.
    
    Args:
        county: County name
        
    Returns:
        Dictionary with region and is_urban
    """
    county_normalized = county.strip()
    
    # Get region
    region = COUNTY_TO_REGION.get(county_normalized, "Unknown")
    
    # Check if urban
    is_urban = county_normalized in URBAN_COUNTIES
    
    return {
        "region": region,
        "is_urban": is_urban
    }


def save_report(data: dict) -> Optional[str]:
    """
    Save a verification report to Firestore.
    
    This function logs anonymized reports for future pattern analysis.
    The data is stored at: /artifacts/mwavuli/public/data/reports
    
    Args:
        data: Dictionary containing:
            - text: The original text that was analyzed
            - risk_level: HIGH, MEDIUM, or LOW
            - language: Detected language (if available)
            - county: Kenyan county (if provided)
            - sender_id: Will be anonymized before storage
            - scores: Raw toxicity scores (optional)
            - matched_keyword: Lexicon keyword if matched (optional)
            
    Returns:
        The generated document ID if successful, None if failed
    """
    db = _get_db()
    
    if db is None:
        print("Database not available. Report not saved.")
        return None
    
    try:
        # Get timestamp
        timestamp = datetime.utcnow()
        
        # Build the anonymized report document
        report = {
            "text": data.get("text", ""),
            "risk_level": data.get("risk_level", "UNKNOWN"),
            "language": data.get("language", "unknown"),
            "county": data.get("county", "unknown"),
            "timestamp": timestamp,
            "sender_hash": _anonymize_sender(data.get("sender_id", "anonymous")),
        }
        
        # Add temporal fields
        temporal_fields = _get_temporal_fields(timestamp)
        report.update(temporal_fields)
        
        # Add content analysis fields
        text = data.get("text", "")
        content_fields = _get_content_analysis(text)
        report.update(content_fields)
        
        # Add detection metadata
        detection_fields = _get_detection_method(data)
        report.update(detection_fields)
        
        # Add geographic fields
        county = data.get("county", "unknown")
        if county != "unknown":
            geo_fields = _get_geographic_fields(county)
            report.update(geo_fields)
        else:
            report["region"] = "Unknown"
            report["is_urban"] = False
        
        # Add optional fields if present
        if "scores" in data:
            report["scores"] = data["scores"]
        
        if "matched_keyword" in data:
            report["matched_keyword"] = data["matched_keyword"]
        
        if "gemini_context_flag" in data:
            report["gemini_context_flag"] = data["gemini_context_flag"]
        
        # Save to Firestore
        # Path: artifacts/mwavuli/public/data/reports
        doc_ref = db.collection("artifacts").document("mwavuli").collection("public").document("data").collection("reports").add(report)
        
        # doc_ref is a tuple (timestamp, document_reference)
        doc_id = doc_ref[1].id
        print(f"Report saved with ID: {doc_id}")
        return doc_id
        
    except Exception as e:
        print(f"Error saving report to Firestore: {e}")
        return None


def get_report(report_id: str) -> Optional[dict]:
    """
    Retrieve a report by its ID.
    
    Args:
        report_id: The document ID of the report
        
    Returns:
        The report data as a dictionary, or None if not found
    """
    db = _get_db()
    
    if db is None:
        return None
    
    try:
        doc_ref = db.collection("artifacts").document("mwavuli").collection("public").document("data").collection("reports").document(report_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        return None
        
    except Exception as e:
        print(f"Error retrieving report: {e}")
        return None


def get_recent_reports(limit: int = 10) -> list:
    """
    Get the most recent reports for monitoring.
    
    Args:
        limit: Maximum number of reports to return
        
    Returns:
        List of report dictionaries
    """
    db = _get_db()
    
    if db is None:
        return []
    
    try:
        reports_ref = db.collection("artifacts").document("mwavuli").collection("public").document("data").collection("reports")
        query = reports_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
        
        reports = []
        for doc in query.stream():
            report = doc.to_dict()
            report["id"] = doc.id
            reports.append(report)
        
        return reports
        
    except Exception as e:
        print(f"Error retrieving recent reports: {e}")
        return []


def is_database_connected() -> bool:
    """
    Check if the database is connected and available.
    
    Returns:
        True if database is connected, False otherwise
    """
    db = _get_db()
    return db is not None
