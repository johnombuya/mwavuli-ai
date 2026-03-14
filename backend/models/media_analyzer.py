"""
Media verification for Project Mwavuli.

Supports images, audio, and video with cost-saving layers:
  1. SHA-256 hash dedup (cached in Supabase media_hashes table)
  2. Tesseract OCR -> text ensemble (images)
  3. Vision LLM (Gemini / Ollama / auto)
  4. Whisper speech-to-text (audio)
  5. Keyframe + audio extraction (video)
"""

import base64
import hashlib
import io
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List

import httpx
from dotenv import load_dotenv

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")

# ---------------------------------------------------------------------------
# Gemini SDK imports
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_MEDIA_BYTES = 50 * 1024 * 1024  # 50 MB (audio/video)
_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")
_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
_OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava")
_OCR_MIN_CHARS = 30  # minimum chars from OCR to trigger text ensemble

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
    transcript: str = ""
    frame_results: List[str] = field(default_factory=list)


# ===================================================================
# 1. Hash-based dedup cache (Supabase media_hashes table)
# ===================================================================

def _get_supabase():
    """Lazy import of the Supabase client."""
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception:
        return None


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _cache_lookup(content_hash: str) -> Optional[MediaAnalysisResult]:
    sb = _get_supabase()
    if not sb:
        return None
    try:
        resp = sb.table("media_hashes").select("*").eq("hash", content_hash).execute()
        if resp.data:
            row = resp.data[0]
            return MediaAnalysisResult(
                risk_level=row["risk_level"],
                explanation=f"[cached] {row.get('explanation', '')}",
            )
    except Exception as e:
        print(f"[media_analyzer] cache lookup error: {e}")
    return None


def _cache_store(content_hash: str, result: MediaAnalysisResult, media_type: str):
    sb = _get_supabase()
    if not sb:
        return
    try:
        sb.table("media_hashes").upsert({
            "hash": content_hash,
            "risk_level": result.risk_level,
            "explanation": result.explanation[:500],
            "media_type": media_type,
        }).execute()
    except Exception as e:
        print(f"[media_analyzer] cache store error: {e}")


# ===================================================================
# 2. Local OCR via Tesseract
# ===================================================================

def _ocr_extract(image_bytes: bytes) -> str:
    """Run Tesseract OCR and return extracted text. Returns '' on failure."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        print(f"[media_analyzer] OCR error (non-fatal): {e}")
        return ""


async def _run_text_ensemble(text: str):
    """Feed text through the Mwavuli text analysis ensemble. Returns AnalysisResult."""
    try:
        from models.text_analyzer import get_analyzer
        analyzer = get_analyzer()
        return await analyzer.analyze(text)
    except Exception as e:
        print(f"[media_analyzer] text ensemble error: {e}")
        return None


# ===================================================================
# 3. Vision LLM helpers (Gemini + Ollama)
# ===================================================================

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


def _parse_vision_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return {}


async def _analyze_image_gemini(image_bytes: bytes, content_type: str) -> Optional[MediaAnalysisResult]:
    client, model = _get_gemini_client()
    if client is None and model is None:
        return None

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
            b64 = base64.b64encode(image_bytes).decode()
            image_part = {"mime_type": content_type, "data": b64}
            response = await model.generate_content_async([_IMAGE_PROMPT, image_part])
            result_text = response.text.strip()
        else:
            return None

        parsed = _parse_vision_json(result_text)
        if not parsed:
            return None
        return MediaAnalysisResult(
            risk_level=parsed.get("risk_level", "MEDIUM"),
            explanation=parsed.get("explanation", ""),
            contains_text=parsed.get("contains_text", False),
            detected_text_summary=parsed.get("detected_text_summary", ""),
        )
    except Exception as e:
        print(f"[media_analyzer] Gemini Vision error: {e}")
        return None


async def _analyze_image_ollama(image_bytes: bytes) -> Optional[MediaAnalysisResult]:
    b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "model": _OLLAMA_VISION_MODEL,
        "prompt": _IMAGE_PROMPT,
        "images": [b64],
        "stream": False,
        "format": "json",
        "system": "You are a JSON API. Return only valid JSON, no explanation.",
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as http:
            resp = await http.post(f"{_OLLAMA_BASE}/api/generate", json=payload)
            resp.raise_for_status()
            body = resp.json()
        raw = body.get("response", "")
        parsed = _parse_vision_json(raw)
        if not parsed:
            return None
        return MediaAnalysisResult(
            risk_level=parsed.get("risk_level", "MEDIUM"),
            explanation=parsed.get("explanation", ""),
            contains_text=parsed.get("contains_text", False),
            detected_text_summary=parsed.get("detected_text_summary", ""),
        )
    except Exception as e:
        print(f"[media_analyzer] Ollama Vision error: {e}")
        return None


async def _vision_analyze(image_bytes: bytes, content_type: str) -> Optional[MediaAnalysisResult]:
    """Route to the configured Vision LLM based on LLM_PROVIDER."""
    if _LLM_PROVIDER == "gemini":
        return await _analyze_image_gemini(image_bytes, content_type)
    if _LLM_PROVIDER == "ollama":
        return await _analyze_image_ollama(image_bytes)
    # auto: try Gemini first, fall back to Ollama
    result = await _analyze_image_gemini(image_bytes, content_type)
    if result:
        return result
    return await _analyze_image_ollama(image_bytes)


# ===================================================================
# 4. Combined image pipeline
# ===================================================================

def _higher_risk(a: str, b: str) -> str:
    order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    return a if order.get(a, 0) >= order.get(b, 0) else b


async def _analyze_image_pipeline(image_bytes: bytes, content_type: str) -> MediaAnalysisResult:
    """Full image analysis: OCR -> text ensemble -> Vision LLM."""
    # OCR pass
    ocr_text = _ocr_extract(image_bytes)
    ensemble_result = None
    if len(ocr_text) >= _OCR_MIN_CHARS:
        ensemble_result = await _run_text_ensemble(ocr_text)
        if ensemble_result and ensemble_result.risk_level in ("HIGH", "MEDIUM"):
            return MediaAnalysisResult(
                risk_level=ensemble_result.risk_level,
                explanation=f"Text detected in image via OCR. {ensemble_result.messages.get('english', '')}",
                contains_text=True,
                detected_text_summary=ocr_text[:300],
            )

    # Vision LLM
    vision_result = await _vision_analyze(image_bytes, content_type)
    if not vision_result:
        if ensemble_result:
            return MediaAnalysisResult(
                risk_level=ensemble_result.risk_level,
                explanation=f"Vision unavailable; OCR text analyzed. {ensemble_result.messages.get('english', '')}",
                contains_text=bool(ocr_text),
                detected_text_summary=ocr_text[:300] if ocr_text else "",
            )
        return MediaAnalysisResult(
            risk_level="MEDIUM",
            explanation="Image analysis unavailable (no Vision LLM configured). Manual review recommended.",
        )

    # If Vision found text, run that through ensemble too and merge
    if vision_result.contains_text and vision_result.detected_text_summary:
        text_result = await _run_text_ensemble(vision_result.detected_text_summary)
        if text_result:
            merged_risk = _higher_risk(vision_result.risk_level, text_result.risk_level)
            vision_result.risk_level = merged_risk
            if text_result.risk_level in ("HIGH", "MEDIUM"):
                vision_result.explanation += f" Text ensemble: {text_result.messages.get('english', '')}"

    return vision_result


# ===================================================================
# 5. Whisper audio analysis
# ===================================================================

async def _analyze_audio_pipeline(audio_bytes: bytes, content_type: str) -> MediaAnalysisResult:
    """Transcribe audio via Whisper, then run text through ensemble."""
    transcript = ""
    try:
        import whisper
        with tempfile.NamedTemporaryFile(suffix=_audio_suffix(content_type), delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        model = whisper.load_model("base")
        result = model.transcribe(tmp_path)
        transcript = result.get("text", "").strip()
    except Exception as e:
        print(f"[media_analyzer] Whisper error: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    if not transcript:
        return MediaAnalysisResult(
            risk_level="LOW",
            explanation="Audio transcription produced no text. Manual review recommended.",
            transcript="",
        )

    ensemble_result = await _run_text_ensemble(transcript)
    if ensemble_result:
        return MediaAnalysisResult(
            risk_level=ensemble_result.risk_level,
            explanation=f"Audio transcript analyzed. {ensemble_result.messages.get('english', '')}",
            transcript=transcript,
        )
    return MediaAnalysisResult(
        risk_level="MEDIUM",
        explanation="Audio transcribed but text analysis unavailable.",
        transcript=transcript,
    )


def _audio_suffix(content_type: str) -> str:
    mapping = {
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
        "audio/mp4": ".m4a",
    }
    return mapping.get(content_type, ".ogg")


# ===================================================================
# 6. Video analysis (keyframe + audio extraction)
# ===================================================================

async def _analyze_video_pipeline(video_bytes: bytes, content_type: str) -> MediaAnalysisResult:
    """Extract keyframes and audio from video, analyze each."""
    suffix = _video_suffix(content_type)
    tmp_dir = tempfile.mkdtemp(prefix="mwavuli_video_")
    video_path = os.path.join(tmp_dir, f"input{suffix}")
    try:
        with open(video_path, "wb") as f:
            f.write(video_bytes)

        frames = _extract_keyframes(video_path, tmp_dir)
        audio_path = _extract_audio(video_path, tmp_dir)

        highest_risk = "LOW"
        explanations = []
        frame_summaries = []

        # Analyze keyframes
        for frame_path in frames:
            with open(frame_path, "rb") as fimg:
                frame_bytes = fimg.read()
            frame_result = await _analyze_image_pipeline(frame_bytes, "image/jpeg")
            highest_risk = _higher_risk(highest_risk, frame_result.risk_level)
            if frame_result.risk_level in ("HIGH", "MEDIUM"):
                explanations.append(f"Frame: {frame_result.explanation}")
            frame_summaries.append(f"{os.path.basename(frame_path)}: {frame_result.risk_level}")

        # Analyze audio track
        transcript = ""
        if audio_path and os.path.exists(audio_path):
            with open(audio_path, "rb") as fa:
                audio_bytes_extracted = fa.read()
            if len(audio_bytes_extracted) > 1000:
                audio_result = await _analyze_audio_pipeline(audio_bytes_extracted, "audio/wav")
                highest_risk = _higher_risk(highest_risk, audio_result.risk_level)
                transcript = audio_result.transcript
                if audio_result.risk_level in ("HIGH", "MEDIUM"):
                    explanations.append(f"Audio: {audio_result.explanation}")

        if not explanations:
            explanation = f"Video analyzed ({len(frames)} frames). No significant risks detected."
        else:
            explanation = " | ".join(explanations[:3])

        return MediaAnalysisResult(
            risk_level=highest_risk,
            explanation=explanation,
            transcript=transcript,
            frame_results=frame_summaries,
        )
    except Exception as e:
        print(f"[media_analyzer] video pipeline error: {e}")
        return MediaAnalysisResult(
            risk_level="MEDIUM",
            explanation=f"Video analysis error: {e}. Manual review recommended.",
        )
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _video_suffix(content_type: str) -> str:
    mapping = {
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
        "video/3gpp": ".3gp",
    }
    return mapping.get(content_type, ".mp4")


def _extract_keyframes(video_path: str, out_dir: str) -> List[str]:
    """Use ffmpeg to extract 1 keyframe every 5 seconds."""
    pattern = os.path.join(out_dir, "frame_%04d.jpg")
    try:
        subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vf", "fps=1/5",
                "-q:v", "2",
                "-frames:v", "20",
                pattern,
            ],
            capture_output=True, timeout=120,
        )
    except FileNotFoundError:
        print("[media_analyzer] ffmpeg not found; skipping keyframe extraction")
        return []
    except subprocess.TimeoutExpired:
        print("[media_analyzer] ffmpeg keyframe extraction timed out")
        return []

    frames = sorted(
        [os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.startswith("frame_")]
    )
    return frames


def _extract_audio(video_path: str, out_dir: str) -> Optional[str]:
    """Use ffmpeg to extract audio track as wav."""
    audio_path = os.path.join(out_dir, "audio.wav")
    try:
        subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vn", "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1",
                audio_path,
            ],
            capture_output=True, timeout=120,
        )
        return audio_path if os.path.exists(audio_path) else None
    except FileNotFoundError:
        print("[media_analyzer] ffmpeg not found; skipping audio extraction")
        return None
    except subprocess.TimeoutExpired:
        print("[media_analyzer] ffmpeg audio extraction timed out")
        return None


# ===================================================================
# 7. Public API: top-level entry points
# ===================================================================

def _detect_media_type(content_type: str) -> str:
    """Infer media category from MIME type."""
    ct = content_type.lower()
    if ct.startswith("image/"):
        return "image"
    if ct.startswith("audio/") or ct == "application/ogg":
        return "audio"
    if ct.startswith("video/"):
        return "video"
    return "unknown"


async def analyze_image(image_url: str = "", *, image_bytes: bytes = b"", content_type: str = "image/jpeg") -> MediaAnalysisResult:
    """Analyze an image by URL or raw bytes. Backwards-compatible with the old signature."""
    if not image_bytes and image_url:
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.get(image_url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg")
            image_bytes = resp.content

    if not image_bytes:
        return MediaAnalysisResult(
            risk_level="MEDIUM",
            explanation="No image data provided.",
        )

    if len(image_bytes) > MAX_IMAGE_BYTES:
        return MediaAnalysisResult(
            risk_level="MEDIUM",
            explanation=f"Image too large ({len(image_bytes) / 1024 / 1024:.1f} MB, max 5 MB). Manual review recommended.",
        )

    # Dedup check
    content_hash = _hash_bytes(image_bytes)
    cached = _cache_lookup(content_hash)
    if cached:
        return cached

    result = await _analyze_image_pipeline(image_bytes, content_type)

    _cache_store(content_hash, result, "image")
    return result


async def analyze_audio(audio_url: str = "", *, audio_bytes: bytes = b"", content_type: str = "audio/ogg") -> MediaAnalysisResult:
    """Analyze audio by URL or raw bytes."""
    if not audio_bytes and audio_url:
        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.get(audio_url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", content_type)
            audio_bytes = resp.content

    if not audio_bytes:
        return MediaAnalysisResult(risk_level="MEDIUM", explanation="No audio data provided.")

    if len(audio_bytes) > MAX_MEDIA_BYTES:
        return MediaAnalysisResult(
            risk_level="MEDIUM",
            explanation=f"Audio too large ({len(audio_bytes) / 1024 / 1024:.1f} MB). Manual review recommended.",
        )

    content_hash = _hash_bytes(audio_bytes)
    cached = _cache_lookup(content_hash)
    if cached:
        return cached

    result = await _analyze_audio_pipeline(audio_bytes, content_type)
    _cache_store(content_hash, result, "audio")
    return result


async def analyze_video(video_url: str = "", *, video_bytes: bytes = b"", content_type: str = "video/mp4") -> MediaAnalysisResult:
    """Analyze video by URL or raw bytes."""
    if not video_bytes and video_url:
        async with httpx.AsyncClient(timeout=60.0) as http:
            resp = await http.get(video_url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", content_type)
            video_bytes = resp.content

    if not video_bytes:
        return MediaAnalysisResult(risk_level="MEDIUM", explanation="No video data provided.")

    if len(video_bytes) > MAX_MEDIA_BYTES:
        return MediaAnalysisResult(
            risk_level="MEDIUM",
            explanation=f"Video too large ({len(video_bytes) / 1024 / 1024:.1f} MB). Manual review recommended.",
        )

    content_hash = _hash_bytes(video_bytes)
    cached = _cache_lookup(content_hash)
    if cached:
        return cached

    result = await _analyze_video_pipeline(video_bytes, content_type)
    _cache_store(content_hash, result, "video")
    return result


async def analyze_media(
    *,
    media_url: str = "",
    media_type: str = "",
    media_bytes: bytes = b"",
    content_type: str = "",
) -> MediaAnalysisResult:
    """
    Unified entry point — routes to image, audio, or video handler.

    Provide either *media_url* (will be fetched) or *media_bytes* + *content_type*.
    *media_type* can be 'image', 'audio', or 'video'.  If omitted, it is inferred
    from *content_type*.
    """
    if not media_type and content_type:
        media_type = _detect_media_type(content_type)
    if not media_type:
        media_type = "image"  # default fallback

    if media_type == "image":
        return await analyze_image(media_url, image_bytes=media_bytes, content_type=content_type or "image/jpeg")
    if media_type == "audio":
        return await analyze_audio(media_url, audio_bytes=media_bytes, content_type=content_type or "audio/ogg")
    if media_type == "video":
        return await analyze_video(media_url, video_bytes=media_bytes, content_type=content_type or "video/mp4")

    return MediaAnalysisResult(
        risk_level="MEDIUM",
        explanation=f"Unsupported media type: {media_type}. Manual review recommended.",
    )
