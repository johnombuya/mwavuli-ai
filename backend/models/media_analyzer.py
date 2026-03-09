"""
Media verification for Project Mwavuli.

Analyses images via Google Gemini Vision for Kenyan-context risk assessment.
Video and audio types return a placeholder response.
"""

import json
import os
from dataclasses import dataclass
from typing import Optional

import httpx
from dotenv import load_dotenv
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")

try:
    from google import genai as genai_new
    GENAI_NEW_API = True
except ImportError:
    genai_new = None
    GENAI_NEW_API = False

try:
    import google.generativeai as genai_old
    GENAI_OLD_AVAILABLE = True
except ImportError:
    genai_old = None
    GENAI_OLD_AVAILABLE = False

if GENAI_NEW_API:
    genai = genai_new
elif GENAI_OLD_AVAILABLE:
    genai = genai_old
else:
    genai = None

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")

_IMAGE_PROMPT = """You are Mwavuli, a Kenyan content safety system. Analyse the image below for harmful, 
misleading, or inciting content in the Kenyan context (political, ethnic, health misinformation, fraud).

Respond ONLY with valid JSON (no markdown fences):
{
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "explanation": "<1-2 sentence explanation in English>",
  "contains_text": true/false,
  "detected_text_summary": "<summary of any text in the image, or empty string>"
}"""


@dataclass
class MediaAnalysisResult:
    risk_level: str
    explanation: str
    contains_text: bool = False
    detected_text_summary: str = ""


def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        return None, None
    if GENAI_NEW_API:
        return genai.Client(api_key=api_key), None
    if GENAI_OLD_AVAILABLE:
        genai.configure(api_key=api_key)
        return None, genai.GenerativeModel(_VISION_MODEL)
    return None, None


async def analyze_image(image_url: str) -> MediaAnalysisResult:
    """Fetch an image from *image_url* and analyse it with Gemini Vision."""
    client, model = _get_gemini_client()
    if client is None and model is None:
        return MediaAnalysisResult(
            risk_level="MEDIUM",
            explanation="Image analysis unavailable (Gemini not configured). Manual review recommended.",
        )

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(image_url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/jpeg")
        image_bytes = resp.content

    if len(image_bytes) > MAX_IMAGE_BYTES:
        return MediaAnalysisResult(
            risk_level="MEDIUM",
            explanation=f"Image too large ({len(image_bytes) / 1024 / 1024:.1f} MB, max 5 MB). Manual review recommended.",
        )

    try:
        if GENAI_NEW_API and client:
            from google.genai import types
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=content_type)
            response = client.models.generate_content(
                model=_VISION_MODEL,
                contents=[_IMAGE_PROMPT, image_part],
            )
            result_text = response.text.strip()
        elif model:
            import base64
            b64 = base64.b64encode(image_bytes).decode()
            image_part = {"mime_type": content_type, "data": b64}
            response = await model.generate_content_async([_IMAGE_PROMPT, image_part])
            result_text = response.text.strip()
        else:
            return MediaAnalysisResult(
                risk_level="MEDIUM",
                explanation="Gemini Vision not available.",
            )

        if result_text.startswith("```"):
            result_text = result_text.strip("`").removeprefix("json").strip()
        parsed = json.loads(result_text)
        return MediaAnalysisResult(
            risk_level=parsed.get("risk_level", "MEDIUM"),
            explanation=parsed.get("explanation", ""),
            contains_text=parsed.get("contains_text", False),
            detected_text_summary=parsed.get("detected_text_summary", ""),
        )
    except Exception as e:
        print(f"[media_analyzer] Gemini Vision error: {e}")
        return MediaAnalysisResult(
            risk_level="MEDIUM",
            explanation=f"Image analysis encountered an error: {e}. Manual review recommended.",
        )
