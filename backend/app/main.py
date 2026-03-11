"""
Project Mwavuli - FastAPI Application

This is the main entry point for the Mwavuli content verification API.
It provides endpoints for analyzing text and media content for harmful
information, with special handling for Kenyan political context.

Run with: uvicorn app.main:app --reload (from backend/ directory)
Or: cd backend && uvicorn app.main:app --reload
"""

import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Query, Request, Header
from fastapi.responses import StreamingResponse, JSONResponse, Response, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from models.text_analyzer import get_analyzer, MwavuliAnalyzer
from utils.db import (
    save_report, is_database_connected, get_ingestion_last_run,
    get_recent_reports, get_repository, _anonymize_sender,
)
from utils import analytics
from utils import export
from utils.twilio_client import is_twilio_configured, send_whatsapp_message, validate_twilio_signature
from utils.audit import log_audit_event
from utils.auth import has_permission


# Pydantic Models
class VerifyTextRequest(BaseModel):
    """Request model for text verification."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to analyze")
    sender_id: str = Field(..., min_length=1, description="Sender identifier (will be anonymized)")
    county: Optional[str] = Field(None, description="Kenyan county for regional context")
    sector: str = Field("political", description="Sector: political, health, security, fraud")
    org_id: Optional[str] = Field(None, description="Organization identifier for multi-tenant isolation")


class VerifyMediaRequest(BaseModel):
    """Request model for media verification (placeholder)."""
    media_url: str = Field(..., description="URL of the media to analyze")
    media_type: str = Field(..., description="Type of media: image, video, audio")
    sender_id: str = Field(..., min_length=1, description="Sender identifier")
    county: Optional[str] = Field(None, description="Kenyan county for regional context")


class TranslatedMessages(BaseModel):
    """Translated response messages."""
    english: str
    swahili: str
    sheng: str


class VerifyResponse(BaseModel):
    """Response model for verification endpoints."""
    risk_level: str = Field(..., description="Risk level: HIGH, MEDIUM, or LOW")
    messages: TranslatedMessages = Field(..., description="Translated warning messages")
    report_id: Optional[str] = Field(None, description="Database report ID for tracking")
    prebunking_tip: str = Field(
        default="For official election results, always visit iebc.or.ke",
        description="Pre-bunking tip for media literacy"
    )
    scores: Optional[Dict[str, float]] = Field(None, description="Raw toxicity scores")
    matched_keyword: Optional[str] = Field(None, description="Matched high-risk keyword if any")
    explanation: Optional[str] = Field(None, description="Human-readable reason for the risk level")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    version: str
    model_loaded: bool


# Analytics Response Models
class RiskDistributionResponse(BaseModel):
    """Response model for risk level distribution."""
    distribution: Dict[str, int]
    total: int


class CountyAnalysisResponse(BaseModel):
    """Response model for county-level analysis."""
    counties: Dict[str, Dict[str, Any]]


class KeywordTrendsResponse(BaseModel):
    """Response model for keyword trends."""
    keywords: List[Dict[str, Any]]
    total_keywords: int


class ToxicityTrendsResponse(BaseModel):
    """Response model for toxicity trends."""
    trends: List[Dict[str, Any]]
    period_days: int


class PatternAnalysisResponse(BaseModel):
    """Response model for temporal patterns."""
    patterns: Dict[str, Any]
    pattern_type: str


class DetectionComparisonResponse(BaseModel):
    """Response model for detection method comparison."""
    comparison: Dict[str, Any]


class GeographicHeatmapResponse(BaseModel):
    """Response model for geographic heatmap."""
    counties: Dict[str, Dict[str, Any]]


class SummaryStatsResponse(BaseModel):
    """Response model for summary statistics."""
    total_reports: int
    risk_distribution: Dict[str, int]
    avg_toxicity: float
    top_keywords: List[Dict[str, Any]]
    top_counties: List[Dict[str, Any]]
    date_range: Dict[str, Optional[str]]


class AnomaliesResponse(BaseModel):
    """Response model for anomaly detection."""
    anomalies: List[Dict[str, Any]]
    threshold: float


class TopTokensResponse(BaseModel):
    """Response model for token-based trends."""
    tokens: List[Dict[str, Any]]


class DetectionRiskMatrixResponse(BaseModel):
    """Response model for detection method vs risk matrix."""
    matrix: Dict[str, Dict[str, Any]]


class ConfidenceHistogramResponse(BaseModel):
    """Response model for confidence score histogram."""
    buckets: List[Dict[str, Any]]


class UrlMentionRiskResponse(BaseModel):
    """Response model for URL/mention risk comparison."""
    stats: Dict[str, Dict[str, Any]]


class StatusSummaryResponse(BaseModel):
    """Response model for moderation status counts."""
    counts: Dict[str, int]
    total: int


# ---- API Key authentication middleware ----
_API_KEYS_RAW = os.getenv("API_KEYS", "")
_API_KEYS = {k.strip() for k in _API_KEYS_RAW.split(",") if k.strip()} if _API_KEYS_RAW else set()

_PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc", "/api/v1/health", "/api/v1/health/data-integrity"}


from starlette.middleware.base import BaseHTTPMiddleware


_ADMIN_PATHS = {"/api/v1/admin/"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests without a valid X-API-Key when API_KEYS env is set.
    Also enforces role-based access for admin endpoints."""

    async def dispatch(self, request: Request, call_next):
        if not _API_KEYS:
            return await call_next(request)
        path = request.url.path
        if path in _PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)
        key = request.headers.get("X-API-Key", "")
        if key not in _API_KEYS:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
        # Role gate for admin-only paths
        if any(path.startswith(p) for p in _ADMIN_PATHS):
            if not has_permission(key, "admin"):
                return JSONResponse(status_code=403, content={"detail": "Admin role required"})
        # Role gate for export paths and report mutations
        if "/export/" in path:
            if not has_permission(key, "analyst"):
                return JSONResponse(status_code=403, content={"detail": "Analyst role required"})
        if request.method == "PATCH" and "/reports/" in path:
            if not has_permission(key, "analyst"):
                return JSONResponse(status_code=403, content={"detail": "Analyst role required"})
        if "/appeals/" in path and "/resolve" in path and request.method == "POST":
            if not has_permission(key, "analyst"):
                return JSONResponse(status_code=403, content={"detail": "Analyst role required"})
        return await call_next(request)


# Global analyzer instance
analyzer: Optional[MwavuliAnalyzer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    global analyzer
    print("Starting Mwavuli API...")
    analyzer = get_analyzer()

    try:
        from datetime import timedelta

        repo = get_repository()
        if repo.is_connected():
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=7)
            aggs = repo.get_aggregate_docs(start_dt, end_dt)
            if not aggs:
                recent = repo.query_reports(limit=1)
                if recent:
                    print(
                        "\n"
                        "##########################################################\n"
                        "# WARNING: Reports exist but report_aggregates is empty! #\n"
                        "# Dashboard analytics will show no data until you run:   #\n"
                        "#                                                        #\n"
                        "#   python scripts/backfill_aggregates.py \\              #\n"
                        "#     --start-date YYYY-MM-DD --end-date YYYY-MM-DD      #\n"
                        "##########################################################\n"
                    )
    except Exception as exc:
        print(f"Startup aggregate check skipped: {exc}")

    print("Mwavuli API ready.")
    yield
    print("Shutting down Mwavuli API...")


# Create FastAPI application
app = FastAPI(
    title="Project Mwavuli API",
    description="Content verification API for detecting harmful information in the Kenyan context",
    version="1.0.0",
    lifespan=lifespan
)


# CORS Middleware - Allow frontend and n8n/Twilio integration
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Next.js dev server
    "http://localhost:3001",  # Alternative port
    os.getenv("FRONTEND_URL", "http://localhost:3000"),  # Production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(APIKeyMiddleware)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the current status of the API and model loading state.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        model_loaded=analyzer is not None
    )


@app.get("/api/v1/health", tags=["System"])
async def api_health():
    """
    Enhanced health check endpoint for frontend and Docker health checks.
    
    Returns detailed service status including database and analyzer state.
    """
    db_status = "connected" if is_database_connected() else "disconnected"
    analyzer_status = "loaded" if analyzer else "not_loaded"
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_status,
            "analyzer": analyzer_status
        }
    }


@app.get("/api/v1/health/data-integrity", tags=["System"])
async def check_data_integrity():
    """Check whether reports and aggregates are in sync and well-formed."""
    from datetime import timedelta

    repo = get_repository()
    issues: List[str] = []

    has_reports = False
    has_aggregates = False
    agg_count = 0

    try:
        recent = repo.query_reports(limit=1)
        has_reports = len(recent) > 0
    except Exception as exc:
        issues.append(f"Could not query reports table: {exc}")

    try:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=30)
        aggs = repo.get_aggregate_docs(start_dt, end_dt)
        agg_count = len(aggs)
        has_aggregates = agg_count > 0

        for agg in aggs[:3]:
            if isinstance(agg.get("risk_counts"), str):
                issues.append(
                    "Aggregates contain double-serialized JSON strings "
                    "-- re-run backfill_aggregates.py"
                )
                break
    except Exception as exc:
        issues.append(f"Could not query report_aggregates table: {exc}")

    if has_reports and not has_aggregates:
        issues.append(
            "Reports exist but report_aggregates is empty "
            "-- run: python scripts/backfill_aggregates.py "
            "--start-date <earliest> --end-date <latest>"
        )

    return {
        "healthy": len(issues) == 0,
        "has_reports": has_reports,
        "has_aggregates": has_aggregates,
        "aggregate_days": agg_count,
        "issues": issues,
    }


@app.post("/api/v1/verify/text", response_model=VerifyResponse, tags=["Verification"])
async def verify_text(request: VerifyTextRequest):
    """
    Verify text content for harmful information.
    
    This endpoint:
    1. Checks for high-risk Kenyan political keywords
    2. Analyzes toxicity using the Detoxify multilingual model
    3. Uses Gemini for Kenyan context analysis and translation
    4. Logs the interaction for pattern analysis
    5. Returns risk level and translated warning messages
    
    The response includes messages in English, Swahili, and Sheng for
    maximum accessibility in the Kenyan context.
    """
    if analyzer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analyzer model not loaded"
        )
    
    try:
        # Per-sender rate limit
        from utils.rate_limit import is_rate_limited
        if is_rate_limited(_anonymize_sender(request.sender_id)):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

        # Analyze the text (pass sector for sector-specific lexicon)
        result = await analyzer.analyze(request.text, sector=request.sector)
        
        # Prepare report data
        report_data = {
            "text": request.text,
            "risk_level": result.risk_level,
            "language": "auto-detect",
            "county": request.county or "unknown",
            "sender_id": request.sender_id,
            "scores": result.scores,
            "sector": request.sector,
        }
        if request.org_id:
            report_data["org_id"] = request.org_id
        
        if result.matched_keyword:
            report_data["matched_keyword"] = result.matched_keyword
        
        if result.gemini_context_flag:
            report_data["gemini_context_flag"] = True
        if result.explanation:
            report_data["explanation"] = result.explanation
        if result.explanation_details:
            report_data["explanation_details"] = result.explanation_details
        report_data["confidence_score"] = result.confidence_score
        if result.kenyan_model_risk:
            report_data["kenyan_model_risk"] = result.kenyan_model_risk
        if result.kenyan_model_score is not None:
            report_data["kenyan_model_score"] = result.kenyan_model_score

        from utils.db import detect_coordinated_activity, get_repository
        sender_hash = _anonymize_sender(request.sender_id)
        is_coordinated = detect_coordinated_activity(sender_hash)

        # Semantic coordination: check if similar content is being posted by multiple senders
        semantic_coord = None
        embedding = report_data.get("embedding")
        if embedding:
            semantic_coord = get_repository().detect_semantic_coordination(embedding)
        if semantic_coord and semantic_coord.get("is_coordinated"):
            is_coordinated = True

        if is_coordinated:
            report_data["coordinated_campaign"] = True

        # Recommended action
        if result.risk_level == "HIGH" and is_coordinated:
            report_data["recommended_action"] = "Escalate to NPS — coordinated campaign"
        elif result.risk_level == "HIGH":
            report_data["recommended_action"] = "Notify county commissioner"
        elif result.risk_level == "MEDIUM":
            report_data["recommended_action"] = "Monitor for 24 h"
        else:
            report_data["recommended_action"] = "Archive"
        
        # Save report to Firestore
        report_id = save_report(report_data)
        
        # Build response
        return VerifyResponse(
            risk_level=result.risk_level,
            messages=TranslatedMessages(
                english=result.messages["english"],
                swahili=result.messages["swahili"],
                sheng=result.messages["sheng"]
            ),
            report_id=report_id,
            prebunking_tip=result.prebunking_tip,
            scores=result.scores,
            matched_keyword=result.matched_keyword,
            explanation=result.explanation,
        )
        
    except Exception as e:
        print(f"Error in text verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@app.post("/api/v1/verify/media", response_model=VerifyResponse, tags=["Verification"])
async def verify_media(request: VerifyMediaRequest):
    """
    Verify media content for harmful information.

    Image verification uses Gemini Vision for Kenyan-context risk assessment.
    Video and audio types return a placeholder awaiting future implementation.
    """
    from utils.rate_limit import is_rate_limited
    import hashlib
    sender_hash = hashlib.sha256(request.sender_id.encode()).hexdigest()[:16]
    if is_rate_limited(sender_hash):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    if request.media_type == "image":
        from models.media_analyzer import analyze_image
        try:
            result = await analyze_image(request.media_url)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image analysis failed: {e}")

        report_data = {
            "text": f"[IMAGE] {request.media_url}",
            "risk_level": result.risk_level,
            "language": "media",
            "county": request.county or "unknown",
            "sender_id": request.sender_id,
            "scores": {},
            "explanation": result.explanation,
            "media_type": "image",
            "media_url": request.media_url,
            "detected_text_summary": result.detected_text_summary,
        }
        report_id = save_report(report_data)

        risk_messages = {
            "HIGH": {
                "english": f"Warning: This image has been assessed as HIGH risk. {result.explanation}",
                "swahili": f"Onyo: Picha hii imetathminiwa kuwa hatari ya JUU. {result.explanation}",
                "sheng": f"Caution: Hii picha imeflagiwa HIGH risk. {result.explanation}",
            },
            "MEDIUM": {
                "english": f"Caution: This image requires attention. {result.explanation}",
                "swahili": f"Tahadhari: Picha hii inahitaji umakini. {result.explanation}",
                "sheng": f"Kaa chonjo: Hii picha inahitaji kuchunguzwa. {result.explanation}",
            },
        }
        msgs = risk_messages.get(result.risk_level, {
            "english": f"This image appears to be low risk. {result.explanation}",
            "swahili": f"Picha hii inaonekana kuwa na hatari ndogo. {result.explanation}",
            "sheng": f"Hii picha inakaa sawa. {result.explanation}",
        })

        return VerifyResponse(
            risk_level=result.risk_level,
            messages=TranslatedMessages(**msgs),
            report_id=report_id,
            prebunking_tip="Always verify images before sharing. Manipulated images spread fast during election periods.",
            scores={},
            matched_keyword=None,
            explanation=result.explanation,
        )

    # Video / audio placeholder
    report_data = {
        "text": f"[MEDIA: {request.media_type}] {request.media_url}",
        "risk_level": "MEDIUM",
        "language": "media",
        "county": request.county or "unknown",
        "sender_id": request.sender_id,
        "scores": {},
        "media_type": request.media_type,
    }
    report_id = save_report(report_data)

    return VerifyResponse(
        risk_level="MEDIUM",
        messages=TranslatedMessages(
            english=f"{request.media_type.title()} verification is not yet supported. This content has been logged for manual review.",
            swahili=f"Uthibitishaji wa {request.media_type} bado haujapatikana. Maudhui haya yamehifadhiwa kwa ukaguzi.",
            sheng=f"{request.media_type.title()} verification haijafika bado. Imelogishwa for manual check.",
        ),
        report_id=report_id,
        prebunking_tip="For official election results, always visit iebc.or.ke",
        scores={},
        matched_keyword=None,
    )


@app.get("/api/v1/analytics/summary", response_model=SummaryStatsResponse, tags=["Analytics"])
async def get_summary_stats(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Get overall statistics summary.
    
    Returns total reports, risk distribution, average toxicity, top keywords, and top counties.
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        stats = await asyncio.to_thread(
            analytics.get_summary_stats,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        response_data = SummaryStatsResponse(**stats)
        
        # Add cache headers (2 minutes) for frontend polling
        import json
        return Response(
            content=json.dumps(response_data.model_dump()),
            media_type="application/json",
            headers={
                "Cache-Control": "public, max-age=120",  # 2 minutes
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving summary stats: {str(e)}"
        )


@app.get("/api/v1/analytics/risk-distribution", response_model=RiskDistributionResponse, tags=["Analytics"])
async def get_risk_distribution(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Get distribution of risk levels.
    
    Returns count of reports by risk level (HIGH, MEDIUM, LOW, UNKNOWN).
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        distribution = await asyncio.to_thread(
            analytics.get_risk_level_distribution,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        total = sum(distribution.values())
        
        response_data = RiskDistributionResponse(distribution=distribution, total=total)
        import json
        return Response(
            content=json.dumps(response_data.model_dump()),
            media_type="application/json",
            headers={"Cache-Control": "public, max-age=120"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving risk distribution: {str(e)}"
        )


@app.get("/api/v1/analytics/county-analysis", response_model=CountyAnalysisResponse, tags=["Analytics"])
async def get_county_analysis(
    county: Optional[str] = Query(None, description="Filter by specific county"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Analyze risk levels by county.
    
    Returns county-level risk breakdown with percentages.
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        analysis = await asyncio.to_thread(
            analytics.get_county_risk_analysis,
            county,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        response = CountyAnalysisResponse(counties=analysis)
        import json
        return Response(
            content=json.dumps(response.model_dump()),
            media_type="application/json",
            headers={"Cache-Control": "public, max-age=120"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving county analysis: {str(e)}"
        )


@app.get("/api/v1/analytics/keyword-trends", response_model=KeywordTrendsResponse, tags=["Analytics"])
async def get_keyword_trends(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of keywords to return"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Get most frequently matched keywords.
    
    Returns top keywords by frequency of detection.
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        keywords = await asyncio.to_thread(
            analytics.get_keyword_trends,
            limit,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        response = KeywordTrendsResponse(keywords=keywords, total_keywords=len(keywords))
        import json
        return Response(
            content=json.dumps(response.model_dump()),
            media_type="application/json",
            headers={"Cache-Control": "public, max-age=120"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving keyword trends: {str(e)}"
        )


@app.get("/api/v1/analytics/toxicity-trends", response_model=ToxicityTrendsResponse, tags=["Analytics"])
async def get_toxicity_trends(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Get average toxicity scores over time.
    
    Returns daily average toxicity scores for trend analysis.
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        trends = await asyncio.to_thread(
            analytics.get_toxicity_trends,
            days,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        response = ToxicityTrendsResponse(trends=trends, period_days=days)
        import json
        return Response(
            content=json.dumps(response.model_dump()),
            media_type="application/json",
            headers={"Cache-Control": "public, max-age=120"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving toxicity trends: {str(e)}"
        )


@app.get("/api/v1/analytics/hourly-patterns", response_model=PatternAnalysisResponse, tags=["Analytics"])
async def get_hourly_patterns(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Analyze when high-risk content is most common by hour of day.
    
    Returns risk distribution by hour (0-23).
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        patterns = await asyncio.to_thread(
            analytics.get_hourly_patterns,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        return PatternAnalysisResponse(patterns=patterns, pattern_type="hourly")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving hourly patterns: {str(e)}"
        )


@app.get("/api/v1/analytics/daily-patterns", response_model=PatternAnalysisResponse, tags=["Analytics"])
async def get_daily_patterns(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Analyze risk distribution by day of week.
    
    Returns risk distribution by day (Monday-Sunday).
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        patterns = await asyncio.to_thread(
            analytics.get_daily_patterns,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        return PatternAnalysisResponse(patterns=patterns, pattern_type="daily")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving daily patterns: {str(e)}"
        )


@app.get("/api/v1/analytics/detection-comparison", response_model=DetectionComparisonResponse, tags=["Analytics"])
async def get_detection_comparison(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Compare Gemini-detected vs lexicon-detected high-risk content.
    
    Returns statistics on detection method effectiveness.
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        comparison = await asyncio.to_thread(
            analytics.get_gemini_vs_lexicon_comparison,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        return DetectionComparisonResponse(comparison=comparison)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving detection comparison: {str(e)}"
        )


@app.get("/api/v1/analytics/detection-risk-matrix", response_model=DetectionRiskMatrixResponse, tags=["Analytics"])
async def get_detection_risk_matrix(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Aggregate counts by detection method and risk level.
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        matrix = await asyncio.to_thread(
            analytics.get_detection_method_risk_matrix,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        return DetectionRiskMatrixResponse(matrix=matrix)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving detection risk matrix: {str(e)}"
        )


@app.get("/api/v1/analytics/confidence-histogram", response_model=ConfidenceHistogramResponse, tags=["Analytics"])
async def get_confidence_histogram(
    bucket_size: float = Query(0.1, ge=0.01, le=0.5, description="Bucket size for confidence bins"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Get histogram of confidence_score across reports.
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        buckets = await asyncio.to_thread(
            analytics.get_confidence_histogram,
            start_dt,
            end_dt,
            bucket_size=bucket_size,
            sector=sector,
            org_id=org_id,
        )
        return ConfidenceHistogramResponse(buckets=buckets)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving confidence histogram: {str(e)}"
        )


@app.get("/api/v1/analytics/url-mention-risk", response_model=UrlMentionRiskResponse, tags=["Analytics"])
async def get_url_mention_risk(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Compare risk distributions for reports with/without URLs and mentions.
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        stats = await asyncio.to_thread(
            analytics.get_url_mention_risk_stats,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        return UrlMentionRiskResponse(stats=stats)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving URL/mention risk stats: {str(e)}"
        )


@app.get("/api/v1/analytics/status-summary", response_model=StatusSummaryResponse, tags=["Analytics"])
async def get_status_summary(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Get counts of reports by moderation status.
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        summary = await asyncio.to_thread(
            analytics.get_status_counts,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        if not summary:
            return StatusSummaryResponse(counts={}, total=0)
        return StatusSummaryResponse(**summary)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving status summary: {str(e)}"
        )


@app.get("/api/v1/analytics/geographic-heatmap", response_model=GeographicHeatmapResponse, tags=["Analytics"])
async def get_geographic_heatmap(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Get county-level risk aggregation for heatmap visualization.
    
    Returns county-level risk scores and statistics.
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        heatmap = await asyncio.to_thread(
            analytics.get_geographic_heatmap,
            start_dt,
            end_dt,
            sector=sector,
            org_id=org_id,
        )
        response = GeographicHeatmapResponse(counties=heatmap)
        import json
        return Response(
            content=json.dumps(response.model_dump()),
            media_type="application/json",
            headers={"Cache-Control": "public, max-age=300"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving geographic heatmap: {str(e)}"
        )
    
    
@app.get("/api/v1/analytics/recent", tags=["Analytics"])
async def get_recent_reports_endpoint(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of reports"),
    status_filter: Optional[str] = Query(
        None,
        description="Filter by status: pending, reviewed, escalated",
    ),
):
    """
    Get most recent reports for monitoring. Optional filter by status.
    """
    try:
        status_param = (status_filter.strip() or None) if status_filter else None
        reports = await asyncio.to_thread(
            get_recent_reports,
            limit,
            status_param,
        )
        return {"reports": reports, "count": len(reports)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving recent reports: {str(e)}",
        )


# Export Endpoints
@app.get("/api/v1/analytics/top-tokens", response_model=TopTokensResponse, tags=["Analytics"])
async def get_top_tokens(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of tokens to return"),
    risk_levels: Optional[str] = Query("HIGH", description="Comma-separated risk levels to include"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    org_id: Optional[str] = Query(None, description="Organization filter"),
):
    """
    Get most frequent tokens from high-risk reports (text-based trends).
    """
    start_date = (start_date or "").strip() or None
    end_date = (end_date or "").strip() or None
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        levels = [
            lvl.strip().upper()
            for lvl in (risk_levels or "").split(",")
            if lvl.strip()
        ]
        if not levels:
            levels = ["HIGH"]

        tokens = await asyncio.to_thread(
            analytics.get_top_tokens,
            limit,
            start_dt,
            end_dt,
            levels,
            sector=sector,
            org_id=org_id,
        )
        return TopTokensResponse(tokens=tokens)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving top tokens: {str(e)}"
        )


@app.get("/api/v1/export/reports", tags=["Export"])
async def export_reports(
    format: str = Query("csv", regex="^(csv|json)$", description="Export format: csv or json"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to include (CSV only)")
):
    """
    Export raw reports data.
    
    Returns reports in CSV or JSON format for analysis or import into Looker Studio.
    """
    try:
        if not start_date or not end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date and end_date are required for exports",
            )
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        # Enforce a maximum export window (e.g. 31 days) to avoid
        # accidentally scanning the entire dataset in one call.
        if (end_dt - start_dt).days > 31:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Export window too large; please request 31 days or less per call",
            )
        
        field_list = [f.strip() for f in fields.split(",")] if fields else None
        
        log_audit_event("export_reports", details={"format": format, "start_date": start_date, "end_date": end_date})

        if format == "csv":
            csv_data = await asyncio.to_thread(
                export.export_reports_to_csv,
                start_dt,
                end_dt,
                field_list,
            )
            if not csv_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No reports found for the specified date range",
                )
            
            filename = f"mwavuli_reports_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            return StreamingResponse(
                iter([csv_data]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        else:  # json
            json_data = await asyncio.to_thread(
                export.export_reports_to_json,
                start_dt,
                end_dt,
                False,
            )
            if not json_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No reports found for the specified date range",
                )
            
            return JSONResponse(
                content=json_data,
                headers={
                    "Content-Disposition": (
                        "attachment; "
                        f"filename=mwavuli_reports_{datetime.utcnow().strftime('%Y%m%d')}.json"
                    )
                },
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting reports: {str(e)}"
        )


@app.get("/api/v1/export/report-pack", tags=["Export"])
async def export_report_pack_endpoint(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
):
    """
    Export a report pack (ZIP with reports.csv, summary.json, and methodology note).
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        zip_bytes = await asyncio.to_thread(
            export.export_report_pack,
            start_dt,
            end_dt,
        )
        filename = f"mwavuli_report_pack_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.zip"
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error building report pack: {str(e)}"
        )


@app.get("/api/v1/export/analytics", tags=["Export"])
async def export_analytics(
    analytics_type: str = Query(..., description="Type: risk_distribution, county_analysis, keyword_trends, toxicity_trends"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
):
    """
    Export aggregated analytics data.
    
    Returns pre-aggregated analytics in CSV format for visualization.
    """
    try:
        if not start_date or not end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date and end_date are required for analytics export",
            )
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        # Limit analytics export to a reasonable window (e.g. 90 days).
        if (end_dt - start_dt).days > 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Analytics export window too large; please request 90 days or less per call",
            )
        
        valid_types = [
            "risk_distribution",
            "county_analysis",
            "keyword_trends",
            "toxicity_trends",
        ]
        if analytics_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Invalid analytics_type. Must be one of: "
                    f"{', '.join(valid_types)}"
                ),
            )
        
        csv_data = await asyncio.to_thread(
            export.export_analytics_to_csv,
            analytics_type,
            start_dt,
            end_dt,
        )
        if not csv_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for the specified analytics type and date range",
            )
        
        filename = (
            f"mwavuli_analytics_{analytics_type}_"
            f"{datetime.utcnow().strftime('%Y%m%d')}.csv"
        )
        return StreamingResponse(
            iter([csv_data]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting analytics: {str(e)}"
        )


@app.get("/api/v1/export/looker-studio", tags=["Export"])
async def export_looker_studio(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
):
    """
    Export optimized data view for Looker Studio.
    
    Returns pre-aggregated data optimized for Looker Studio visualization.
    This endpoint provides a comprehensive view with all key metrics.
    """
    try:
        if not start_date or not end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date and end_date are required for Looker Studio export",
            )
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        # Looker Studio views can cover larger windows, but still cap to
        # prevent unbounded scans.
        if (end_dt - start_dt).days > 180:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Looker Studio export window too large; please request 180 days or less per call",
            )
        
        view_data = await asyncio.to_thread(
            export.create_looker_studio_view,
            start_dt,
            end_dt,
        )
        
        if not view_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for the specified date range",
            )
        
        return JSONResponse(content=view_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating Looker Studio view: {str(e)}"
        )


# ----- Twilio WhatsApp Webhook -----


@app.get("/api/v1/webhooks/twilio", tags=["WhatsApp"])
async def twilio_webhook_get():
    """
    Twilio WhatsApp 'Validate URL' callback (GET).
    Return 200 so Twilio accepts the webhook URL.
    """
    return PlainTextResponse("Mwavuli webhook OK", status_code=200)


@app.post("/api/v1/webhooks/twilio", tags=["WhatsApp"])
async def twilio_webhook_post(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None, alias="X-Twilio-Signature"),
):
    """
    Twilio WhatsApp incoming message webhook.

    When a user sends a message to your Twilio WhatsApp number, Twilio POSTs
    here with Body, From, To, etc. We analyze the text, save a report, and
    send back a verification result + prebunking tip in English (and optionally
    Swahili for HIGH/MEDIUM risk).

    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM in .env.
    Configure this URL in Twilio Console: Messaging > Try it out > WhatsApp Sandbox
    (or your WhatsApp Sender) > When a message comes in.
    """
    # Parse form body (Twilio sends application/x-www-form-urlencoded)
    form = await request.form()
    params = dict(form)

    # Optional: validate Twilio signature
    if x_twilio_signature:
        url = str(request.url)
        if not validate_twilio_signature(url, params, x_twilio_signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    body = (params.get("Body") or "").strip()
    from_number = (params.get("From") or "").strip()

    if not body:
        # Could reply "Send a message to verify" if Twilio is configured
        return PlainTextResponse("", status_code=200)

    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}" if from_number.startswith("+") else f"whatsapp:+{from_number}"

    if analyzer is None:
        if is_twilio_configured():
            send_whatsapp_message(
                from_number,
                "Mwavuli is temporarily unavailable. Please try again later.",
            )
        return PlainTextResponse("", status_code=200)

    try:
        result = await analyzer.analyze(body)
    except Exception as e:
        print(f"Twilio webhook analyze error: {e}")
        if is_twilio_configured():
            send_whatsapp_message(
                from_number,
                "We couldn't analyze that message. Please try again or send a shorter text.",
            )
        return PlainTextResponse("", status_code=200)

    # Save report (sender_id = From for anonymized hashing)
    report_data = {
        "text": body,
        "risk_level": result.risk_level,
        "language": "auto-detect",
        "county": "unknown",
        "sender_id": from_number,
        "scores": result.scores,
    }
    if result.matched_keyword:
        report_data["matched_keyword"] = result.matched_keyword
    if result.gemini_context_flag:
        report_data["gemini_context_flag"] = True
    save_report(report_data)

    # Build reply: main message + prebunking tip
    reply = result.messages["english"]
    if result.prebunking_tip:
        reply += "\n\n" + result.prebunking_tip

    # For HIGH/MEDIUM, append Swahili so users can share with others
    if result.risk_level in ("HIGH", "MEDIUM"):
        reply += "\n\n--- Swahili ---\n" + result.messages["swahili"]

    if is_twilio_configured():
        ok, err = send_whatsapp_message(from_number, reply)
        if not ok:
            print(f"Twilio send error: {err}")

    return PlainTextResponse("", status_code=200)


@app.get("/api/v1/analytics/national-risk-level", tags=["Analytics"])
async def get_national_risk_level():
    """Traffic-light national risk indicator (RED/AMBER/GREEN)."""
    try:
        result = await asyncio.to_thread(analytics.get_national_risk_level)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/daily-summary", tags=["Analytics"])
async def get_daily_summary():
    """Natural language summary of the last 24 hours."""
    from datetime import timedelta
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(hours=24)
    try:
        stats = await asyncio.to_thread(analytics.get_summary_stats, start_dt, end_dt)
        total = stats.get("total_reports", 0)
        risk_dist = stats.get("risk_distribution", {})
        top_kw = stats.get("top_keywords", [])
        top_counties = stats.get("top_counties", [])

        kw_str = ", ".join(f"{k['keyword']} ({k['count']})" for k in top_kw[:5]) or "none"
        county_str = ", ".join(f"{c['county']} ({c['count']})" for c in top_counties[:3]) or "none"

        summary = (
            f"In the last 24 hours, {total} reports were analyzed. "
            f"Risk breakdown: {risk_dist.get('HIGH', 0)} HIGH, "
            f"{risk_dist.get('MEDIUM', 0)} MEDIUM, {risk_dist.get('LOW', 0)} LOW. "
            f"Top keywords: {kw_str}. Top counties: {county_str}."
        )
        return {"summary": summary, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/coordinated-campaigns", tags=["Analytics"])
async def get_coordinated_campaigns_endpoint(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Return reports flagged as coordinated campaigns with sender/risk metadata."""
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        results = await asyncio.to_thread(analytics.get_coordinated_campaigns, start_dt, end_dt)
        if isinstance(results, dict):
            return results
        return {"campaigns": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/topic-clusters", tags=["Analytics"])
async def get_topic_clusters_endpoint():
    """Return active narrative clusters discovered by HDBSCAN."""
    try:
        clusters = await asyncio.to_thread(analytics.get_topic_clusters, True)
        return {"clusters": clusters, "count": len(clusters)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/lexicon-suggestions", tags=["Analytics"])
async def get_lexicon_suggestions_endpoint(
    min_high_pct: float = Query(30.0, description="Minimum HIGH-risk % for a cluster to contribute"),
    top_n: int = Query(20, description="Max suggestions to return"),
):
    """Suggest new keywords from high-risk clusters not already in the lexicon."""
    try:
        suggestions = await asyncio.to_thread(
            analytics.get_lexicon_suggestions, min_high_pct, top_n
        )
        return {"suggestions": suggestions, "count": len(suggestions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from utils.emergency_config import get_emergency_mode as _get_em, set_emergency_mode as _set_em


@app.get("/api/v1/admin/emergency-mode", tags=["Admin"])
async def get_emergency_mode():
    return {"emergency_mode": _get_em()}


@app.post("/api/v1/admin/emergency-mode", tags=["Admin"])
async def toggle_emergency_mode(enable: bool = True):
    _set_em(enable)
    log_audit_event("emergency_mode_toggle", details={"enabled": enable})
    return {"emergency_mode": _get_em()}


@app.get("/api/v1/admin/audit-logs", tags=["Admin"])
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    action: Optional[str] = Query(None, description="Filter by action type"),
):
    """Retrieve recent audit log entries (admin only)."""
    repo = get_repository()
    if not repo.is_connected():
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        logs = repo.get_audit_logs(limit=limit, action=action)
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateReportStatusRequest(BaseModel):
    status: str = Field(..., description="New status: pending, reviewed, or escalated")


@app.patch("/api/v1/reports/{report_id}", tags=["Reports"])
async def update_report_status_endpoint(report_id: str, body: UpdateReportStatusRequest):
    """Update a report's moderation status (analyst or admin)."""
    ok = get_repository().update_report_status(report_id, body.status)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid status or report not found")
    log_audit_event("update_report_status", details={"report_id": report_id, "status": body.status})
    return {"report_id": report_id, "status": body.status}


class AppealRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000, description="Reason for the appeal")


@app.post("/api/v1/reports/{report_id}/appeal", tags=["Reports"])
async def appeal_report(report_id: str, appeal: AppealRequest):
    """Submit an appeal for a flagged report."""
    repo = get_repository()
    report = repo.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        appeal_id = repo.create_appeal({
            "report_id": report_id,
            "reason": appeal.reason,
            "status": "pending",
            "timestamp": datetime.utcnow(),
            "original_risk_level": report.get("risk_level"),
        })
        if appeal_id is None:
            raise HTTPException(status_code=503, detail="Database unavailable")
        log_audit_event("report_appeal_submitted", details={"report_id": report_id})
        return {"appeal_id": appeal_id, "status": "pending"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/reports/appeals", tags=["Reports"])
async def list_appeals(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    report_id: Optional[str] = Query(None),
):
    """List report appeals, optionally filtered by status or report_id."""
    repo = get_repository()
    if not repo.is_connected():
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        appeals = repo.list_appeals(status=status, limit=limit, report_id=report_id)
        return {"appeals": appeals, "count": len(appeals)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ResolveAppealRequest(BaseModel):
    resolution: str = Field(..., description="upheld or overturned")
    notes: Optional[str] = Field(None, max_length=2000)


@app.post("/api/v1/reports/appeals/{appeal_id}/resolve", tags=["Reports"])
async def resolve_appeal(appeal_id: str, body: ResolveAppealRequest):
    """Resolve a pending appeal (analyst or admin)."""
    if body.resolution not in ("upheld", "overturned"):
        raise HTTPException(status_code=400, detail="resolution must be 'upheld' or 'overturned'")
    repo = get_repository()
    if not repo.is_connected():
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        appeal_data = repo.get_appeal(appeal_id)
        if appeal_data is None:
            raise HTTPException(status_code=404, detail="Appeal not found")
        update: dict = {
            "status": "resolved",
            "resolved_at": datetime.utcnow(),
            "resolution": body.resolution,
        }
        if body.notes:
            update["notes"] = body.notes
        repo.resolve_appeal(appeal_id, update)
        if body.resolution == "overturned":
            linked_report_id = appeal_data.get("report_id")
            if linked_report_id:
                repo.update_report_status(linked_report_id, "reviewed")
        log_audit_event("appeal_resolved", details={
            "appeal_id": appeal_id,
            "resolution": body.resolution,
        })
        return {"appeal_id": appeal_id, "status": "resolved", "resolution": body.resolution}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/export/stix", tags=["Export"])
async def export_stix(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Export HIGH-risk reports as a STIX 2.1 bundle."""
    import json as _json, uuid as _uuid
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date: {e}")

    repo = get_repository()
    if not repo.is_connected():
        raise HTTPException(status_code=503, detail="Database unavailable")

    high_reports = await asyncio.to_thread(
        repo.query_reports,
        start_date=start_dt,
        end_date=end_dt,
        risk_level="HIGH",
        limit=500,
        order_by_timestamp="asc",
    )

    objects = []
    identity_id = f"identity--{_uuid.uuid5(_uuid.NAMESPACE_URL, 'mwavuli')}"
    objects.append({
        "type": "identity",
        "spec_version": "2.1",
        "id": identity_id,
        "created": datetime.utcnow().isoformat() + "Z",
        "modified": datetime.utcnow().isoformat() + "Z",
        "name": "Project Mwavuli",
        "identity_class": "system",
    })

    for d in high_reports:
        report_id = d.get("id", "")
        ts = d.get("timestamp")
        ts_str = ts.isoformat() + "Z" if hasattr(ts, "isoformat") else str(ts)
        indicator_id = f"indicator--{_uuid.uuid5(_uuid.NAMESPACE_URL, report_id)}"
        objects.append({
            "type": "indicator",
            "spec_version": "2.1",
            "id": indicator_id,
            "created": ts_str,
            "modified": ts_str,
            "name": f"HIGH-risk content ({d.get('matched_keyword', 'N/A')})",
            "description": d.get("explanation", ""),
            "indicator_types": ["malicious-activity"],
            "pattern": f"[content:value = '{report_id}']",
            "pattern_type": "stix",
            "valid_from": ts_str,
            "created_by_ref": identity_id,
            "labels": ["hate-speech", d.get("sector", "political")],
        })

    bundle = {
        "type": "bundle",
        "id": f"bundle--{_uuid.uuid4()}",
        "objects": objects,
    }
    log_audit_event("export_stix", details={"count": len(objects) - 1})
    return JSONResponse(content=bundle, headers={"Content-Disposition": "attachment; filename=mwavuli_stix.json"})


@app.post("/api/v1/webhooks/africastalking", tags=["SMS"])
async def africastalking_sms_webhook(request: Request):
    """
    Africa's Talking incoming SMS webhook.
    Parse the SMS, run through analyzer, and reply with risk assessment.
    """
    form = await request.form()
    text = (form.get("text") or "").strip()
    sender = (form.get("from") or "").strip()

    if not text or analyzer is None:
        return JSONResponse(content={"status": "ignored"})

    try:
        result = await analyzer.analyze(text)
    except Exception as e:
        print(f"[AT SMS] analyze error: {e}")
        return JSONResponse(content={"status": "error"})

    report_data = {
        "text": text,
        "risk_level": result.risk_level,
        "language": "auto-detect",
        "county": "unknown",
        "sender_id": sender,
        "scores": result.scores,
        "sector": "political",
    }
    if result.matched_keyword:
        report_data["matched_keyword"] = result.matched_keyword
    save_report(report_data)

    reply = result.messages.get("english", "")
    try:
        import africastalking
        at_username = os.getenv("AT_USERNAME", "sandbox")
        at_api_key = os.getenv("AT_API_KEY", "")
        if at_api_key:
            africastalking.initialize(at_username, at_api_key)
            sms = africastalking.SMS
            sms.send(reply[:160], [sender])
    except Exception as e:
        print(f"[AT SMS] send error: {e}")

    return JSONResponse(content={"status": "ok", "risk_level": result.risk_level})


@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "Project Mwavuli API",
        "description": "Content verification for combating election misinformation in Kenya",
        "notice": "This system is designed for harm reduction, not surveillance.",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "verify_text": "/api/v1/verify/text",
            "verify_media": "/api/v1/verify/media",
            "webhooks": {
                "twilio_whatsapp": "/api/v1/webhooks/twilio",
            },
            "analytics": {
                "summary": "/api/v1/analytics/summary",
                "risk_distribution": "/api/v1/analytics/risk-distribution",
                "county_analysis": "/api/v1/analytics/county-analysis",
                "keyword_trends": "/api/v1/analytics/keyword-trends",
                "toxicity_trends": "/api/v1/analytics/toxicity-trends",
                "hourly_patterns": "/api/v1/analytics/hourly-patterns",
                "daily_patterns": "/api/v1/analytics/daily-patterns",
                "detection_comparison": "/api/v1/analytics/detection-comparison",
                "geographic_heatmap": "/api/v1/analytics/geographic-heatmap"
            },
            "export": {
                "reports": "/api/v1/export/reports",
                "analytics": "/api/v1/export/analytics",
                "looker_studio": "/api/v1/export/looker-studio"
            }
        },
        "documentation": "/docs"
    }


@app.get("/api/v1/ingestion/status", tags=["Ingestion"])
async def ingestion_status():
    """
    Last ingestion run summary (counts, job_id, timestamp).
    Only available when INGESTION_ADMIN_ENABLED is true.
    """
    from utils import ingestion_config
    if not ingestion_config.is_ingestion_admin_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ingestion admin endpoint is disabled"
        )
    last = get_ingestion_last_run()
    if last is None:
        return {"status": "no_run_yet", "last_run": None}
    return {"status": "ok", "last_run": last}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

