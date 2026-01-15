"""
Firebase Firestore Database Utility for Project Mwavuli.

This module handles all database operations for logging verification reports.
Reports are stored anonymously for future pattern analysis and improving
the detection models.
"""

import os
import hashlib
from datetime import datetime
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
        # Get service account path from environment
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        
        if not service_account_path:
            print("Warning: FIREBASE_SERVICE_ACCOUNT_PATH not set. Database logging disabled.")
            _initialized = True
            return None
        
        if not os.path.exists(service_account_path):
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
        # Build the anonymized report document
        report = {
            "text": data.get("text", ""),
            "risk_level": data.get("risk_level", "UNKNOWN"),
            "language": data.get("language", "unknown"),
            "county": data.get("county", "unknown"),
            "timestamp": datetime.utcnow(),
            "sender_hash": _anonymize_sender(data.get("sender_id", "anonymous")),
        }
        
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

