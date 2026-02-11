"""
Project Mwavuli - FastAPI Application

This is the main entry point for the Mwavuli content verification API.
It provides endpoints for analyzing text and media content for harmful
information, with special handling for Kenyan political context.

Run with: uvicorn app.main:app --reload (from backend/ directory)
Or: cd backend && uvicorn app.main:app --reload
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Query, Request, Header
from fastapi.responses import StreamingResponse, JSONResponse, Response, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from models.text_analyzer import get_analyzer, MwavuliAnalyzer
from utils.db import save_report, is_database_connected
from utils import analytics
from utils import export
from utils.twilio_client import is_twilio_configured, send_whatsapp_message, validate_twilio_signature


# Pydantic Models
class VerifyTextRequest(BaseModel):
    """Request model for text verification."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to analyze")
    sender_id: str = Field(..., min_length=1, description="Sender identifier (will be anonymized)")
    county: Optional[str] = Field(None, description="Kenyan county for regional context")


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


# Global analyzer instance
analyzer: Optional[MwavuliAnalyzer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    global analyzer
    print("Starting Mwavuli API...")
    # Load the analyzer on startup
    analyzer = get_analyzer()
    print("Mwavuli API ready.")
    yield
    # Cleanup on shutdown
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
    allow_methods=["GET", "POST", "OPTIONS"],  # Frontend only needs GET and POST
    allow_headers=["*"],
)


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
        # Analyze the text
        result = await analyzer.analyze(request.text)
        
        # Prepare report data
        report_data = {
            "text": request.text,
            "risk_level": result.risk_level,
            "language": "auto-detect",  # Could be enhanced with language detection
            "county": request.county or "unknown",
            "sender_id": request.sender_id,
            "scores": result.scores,
        }
        
        if result.matched_keyword:
            report_data["matched_keyword"] = result.matched_keyword
        
        if result.gemini_context_flag:
            report_data["gemini_context_flag"] = True
        
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
            matched_keyword=result.matched_keyword
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
    Verify media content for deepfakes and harmful information.
    
    **PLACEHOLDER ENDPOINT**
    
    This endpoint is a placeholder for future deepfake detection functionality.
    Currently returns a mock HIGH risk response for testing purposes.
    
    In future versions, this will:
    1. Download and analyze media content
    2. Detect AI-generated or manipulated images/videos
    3. Check for known misinformation content
    4. Return appropriate risk levels and guidance
    """
    # Mock response for testing - always returns HIGH risk
    mock_report_data = {
        "text": f"[MEDIA: {request.media_type}] {request.media_url}",
        "risk_level": "HIGH",
        "language": "media",
        "county": request.county or "unknown",
        "sender_id": request.sender_id,
        "scores": {"deepfake_detection": 0.85},
    }
    
    # Save mock report
    report_id = save_report(mock_report_data)
    
    return VerifyResponse(
        risk_level="HIGH",
        messages=TranslatedMessages(
            english="Warning: Media content verification is in development. This media has been flagged for manual review. Do not share unverified media during the election period.",
            swahili="Onyo: Uthibitishaji wa maudhui ya media unaendelezwa. Media hii imewekwa alama kwa ukaguzi wa mikono. Usishiriki media ambayo haijathibitishwa wakati wa uchaguzi.",
            sheng="Heads up: Media verification bado inafanyiwa kazi. Hii media imeflagiwa for manual check. Usishare media bila kuthibitisha during elections."
        ),
        report_id=report_id,
        prebunking_tip="For official election results, always visit iebc.or.ke",
        scores={"deepfake_detection": 0.85, "placeholder": True},
        matched_keyword=None
    )


@app.get("/api/v1/analytics/summary", response_model=SummaryStatsResponse, tags=["Analytics"])
async def get_summary_stats(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
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
        
        stats = analytics.get_summary_stats(start_dt, end_dt)
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
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
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
        
        distribution = analytics.get_risk_level_distribution(start_dt, end_dt)
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
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
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
        
        analysis = analytics.get_county_risk_analysis(county, start_dt, end_dt)
        return CountyAnalysisResponse(counties=analysis)
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
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
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
        
        keywords = analytics.get_keyword_trends(limit, start_dt, end_dt)
        return KeywordTrendsResponse(keywords=keywords, total_keywords=len(keywords))
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
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
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
        
        trends = analytics.get_toxicity_trends(days, start_dt, end_dt)
        return ToxicityTrendsResponse(trends=trends, period_days=days)
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
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
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
        
        patterns = analytics.get_hourly_patterns(start_dt, end_dt)
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
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
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
        
        patterns = analytics.get_daily_patterns(start_dt, end_dt)
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
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
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
        
        comparison = analytics.get_gemini_vs_lexicon_comparison(start_dt, end_dt)
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


@app.get("/api/v1/analytics/geographic-heatmap", response_model=GeographicHeatmapResponse, tags=["Analytics"])
async def get_geographic_heatmap(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)")
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
        
        heatmap = analytics.get_geographic_heatmap(start_dt, end_dt)
        return GeographicHeatmapResponse(counties=heatmap)
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


# Export Endpoints
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
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        field_list = [f.strip() for f in fields.split(",")] if fields else None
        
        if format == "csv":
            csv_data = export.export_reports_to_csv(start_dt, end_dt, field_list)
            if not csv_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No reports found for the specified date range"
                )
            
            filename = f"mwavuli_reports_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            return StreamingResponse(
                iter([csv_data]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:  # json
            json_data = export.export_reports_to_json(start_dt, end_dt, flatten=False)
            if not json_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No reports found for the specified date range"
                )
            
            return JSONResponse(
                content=json_data,
                headers={"Content-Disposition": f"attachment; filename=mwavuli_reports_{datetime.utcnow().strftime('%Y%m%d')}.json"}
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
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        valid_types = ["risk_distribution", "county_analysis", "keyword_trends", "toxicity_trends"]
        if analytics_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid analytics_type. Must be one of: {', '.join(valid_types)}"
            )
        
        csv_data = export.export_analytics_to_csv(analytics_type, start_dt, end_dt)
        if not csv_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for the specified analytics type and date range"
            )
        
        filename = f"mwavuli_analytics_{analytics_type}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        return StreamingResponse(
            iter([csv_data]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
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
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        view_data = export.create_looker_studio_view(start_dt, end_dt)
        
        if not view_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for the specified date range"
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


@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "Project Mwavuli API",
        "description": "Content verification for combating election misinformation in Kenya",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

