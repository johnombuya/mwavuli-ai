"""
Project Mwavuli - FastAPI Application

This is the main entry point for the Mwavuli content verification API.
It provides endpoints for analyzing text and media content for harmful
information, with special handling for Kenyan political context.

Run with: uvicorn main:app --reload
"""

from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from models.text_analyzer import get_analyzer, MwavuliAnalyzer
from utils.db import save_report


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


# CORS Middleware for n8n/Twilio integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
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
            "verify_media": "/api/v1/verify/media"
        },
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

