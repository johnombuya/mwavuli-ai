"""
Mwavuli Text Analyzer - Core AI logic for content verification.

This module combines:
1. Lexicon checking for immediate high-risk keyword detection
2. Detoxify multilingual model for toxicity scoring
3. Google Gemini for translation and Kenyan context analysis

The analyzer is designed for the Kenyan election context, with special
handling for local political language and metaphors.
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass

from detoxify import Detoxify
# Try new Google GenAI API first, fallback to deprecated one
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

# Set the active genai module
if GENAI_NEW_API:
    genai = genai_new
elif GENAI_OLD_AVAILABLE:
    genai = genai_old
    print("Using deprecated google.generativeai - consider upgrading to google-genai")
else:
    genai = None
    print("Warning: No Google GenAI package found. Gemini features will be disabled.")

from dotenv import load_dotenv

from utils.lexicon import check_lexicon, get_keyword_context
from models import kenyan_classifier

# Load environment variables
load_dotenv()

# Pre-bunking tip for all responses
PREBUNKING_TIP = "For official election results, always visit iebc.or.ke"

# Ollama / local LLM config
_LOCAL_LLM_ENABLED = os.getenv("LOCAL_LLM_ENABLED", "false").lower() == "true"
_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")

# Ensemble confidence weights (configurable via env)
_W_LEXICON = float(os.getenv("ENSEMBLE_W_LEXICON", "0.30"))
_W_DETOXIFY = float(os.getenv("ENSEMBLE_W_DETOXIFY", "0.25"))
_W_KENYAN = float(os.getenv("ENSEMBLE_W_KENYAN", "0.25"))
_W_GEMINI = float(os.getenv("ENSEMBLE_W_GEMINI", "0.20"))


@dataclass
class AnalysisResult:
    """Result of text analysis."""
    risk_level: str  # HIGH, MEDIUM, LOW
    scores: Dict[str, float]  # Raw toxicity scores
    messages: Dict[str, str]  # Translated messages
    matched_keyword: Optional[str] = None
    gemini_context_flag: bool = False
    prebunking_tip: str = PREBUNKING_TIP
    explanation: Optional[str] = None
    confidence_score: float = 0.0
    kenyan_model_risk: Optional[str] = None
    kenyan_model_score: Optional[float] = None
    explanation_details: Optional[Dict] = None


class MwavuliAnalyzer:
    """
    Main analyzer class for Project Mwavuli.
    
    Combines lexicon checks, Detoxify toxicity detection, and Gemini
    for translation and context-aware analysis of Kenyan political content.
    """
    
    def __init__(self):
        """Initialize the analyzer with Detoxify and Gemini models."""
        print("Initializing MwavuliAnalyzer...")
        
        # Lazy loading - don't load Detoxify until first use
        self.detoxify_model = None
        self._detoxify_loading = False
        self._detoxify_error = None

        # Gemini circuit breaker state
        self._gemini_consecutive_failures = 0
        self._gemini_circuit_open_until = 0.0  # epoch seconds
        
        # Initialize Gemini
        self._init_gemini()
        print("MwavuliAnalyzer initialization complete (Detoxify will load on first use).")
    
    def _init_gemini(self):
        """Initialize Google Gemini API."""
        if genai is None:
            print("Warning: Google GenAI package not installed. Translation and context features disabled.")
            self.gemini_client = None
            self.gemini_model = None
            return
        
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key or api_key == "your_gemini_api_key_here":
            print("Warning: GEMINI_API_KEY not set. Translation and context features disabled.")
            self.gemini_client = None
            self.gemini_model = None
            return
        
        try:
            if GENAI_NEW_API:
                # New API (google.genai) - uses Client pattern
                self.gemini_client = genai.Client(api_key=api_key)
                self.gemini_model = None  # Not needed for new API
                print("Gemini client initialized (using new google.genai API).")
            else:
                # Deprecated API (google.generativeai)
                genai.configure(api_key=api_key)
                self.gemini_client = None
                self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
                print("Gemini model initialized (using deprecated google.generativeai API).")
        except Exception as e:
            print(f"Warning: Failed to initialize Gemini: {e}")
            self.gemini_client = None
            self.gemini_model = None
    
    def _gemini_available(self) -> bool:
        """Return False if the Gemini circuit breaker is open."""
        import time as _time
        if self._gemini_circuit_open_until > _time.time():
            return False
        if self.gemini_client is None and self.gemini_model is None:
            return False
        return True

    def _record_gemini_failure(self):
        import time as _time
        self._gemini_consecutive_failures += 1
        if self._gemini_consecutive_failures >= 5:
            self._gemini_circuit_open_until = _time.time() + 60
            print("[circuit-breaker] Gemini circuit open for 60 s")

    def _record_gemini_success(self):
        self._gemini_consecutive_failures = 0

    async def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call the local Ollama LLM; returns response text or None."""
        if not _LOCAL_LLM_ENABLED:
            return None
        import urllib.request, json as _json
        url = f"{_OLLAMA_BASE_URL}/api/generate"
        body = _json.dumps({"model": _OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode()
        try:
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read().decode())
                return data.get("response", "").strip()
        except Exception as e:
            print(f"[ollama] Error: {e}")
            return None

    def _ensure_detoxify_loaded(self):
        """
        Lazy load Detoxify model on first use.
        Handles corrupted downloads by providing clear error messages.
        """
        if self.detoxify_model is not None:
            return True
        
        if self._detoxify_loading:
            # Already loading, wait a bit
            import time
            time.sleep(1)
            return self.detoxify_model is not None
        
        if self._detoxify_error:
            # Previous load failed, don't retry automatically
            return False
        
        self._detoxify_loading = True
        
        try:
            print("Loading Detoxify multilingual model (first use)...")
            self.detoxify_model = Detoxify('multilingual')
            print("Detoxify model loaded successfully.")
            self._detoxify_loading = False
            return True
        except RuntimeError as e:
            if "failed finding central directory" in str(e) or "zip archive" in str(e):
                print("ERROR: Detoxify model download appears corrupted.")
                print("To fix this, clear the cache manually:")
                print("  PowerShell: Remove-Item -Recurse -Force $env:USERPROFILE\\.cache\\torch\\hub\\*")
                print("  Or manually delete: C:\\Users\\<YourUser>\\.cache\\torch\\hub\\")
                print("Then restart the server - the model will download fresh.")
                self._detoxify_error = "Corrupted cache - please clear manually"
                self._detoxify_loading = False
                return False
            else:
                print(f"Error loading Detoxify model: {e}")
                self._detoxify_error = str(e)
                self._detoxify_loading = False
                return False
        except Exception as e:
            print(f"Error loading Detoxify model: {e}")
            self._detoxify_error = str(e)
            self._detoxify_loading = False
            return False
    
    def _get_detoxify_scores(self, text: str) -> Dict[str, float]:
        """
        Get toxicity scores from Detoxify.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary of toxicity category scores
        """
        # Ensure model is loaded
        if not self._ensure_detoxify_loaded():
            # Fallback: return medium risk if model unavailable
            print("Warning: Detoxify model unavailable, using fallback scoring.")
            return {"toxicity": 0.5, "fallback": True}
        
        try:
            results = self.detoxify_model.predict(text)
            # Convert numpy floats to Python floats
            return {k: float(v) for k, v in results.items()}
        except Exception as e:
            print(f"Error in Detoxify prediction: {e}")
            return {"toxicity": 0.5, "error": True}
    
    def _get_max_toxicity_score(self, scores: Dict[str, float]) -> float:
        """Get the maximum toxicity score across all categories."""
        if "error" in scores or "fallback" in scores:
            return 0.5  # Default to medium on error
        # Filter out non-score keys
        score_values = [v for k, v in scores.items() if k not in ["error", "fallback"]]
        if not score_values:
            return 0.5
        return max(score_values)
    
    def _map_score_to_risk(self, score: float) -> str:
        """
        Map a toxicity score to a risk level.
        
        Args:
            score: Toxicity score between 0 and 1
            
        Returns:
            Risk level: HIGH (>0.7), MEDIUM (0.4-0.7), LOW (<0.4)
        """
        if score > 0.7:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _check_kenyan_context(self, text: str) -> tuple[bool, str]:
        """
        Use Gemini to check for subtle Kenyan political incitement.
        
        This catches metaphors and coded language that standard models miss.
        
        Args:
            text: The text to analyze
            
        Returns:
            Tuple of (is_flagged, explanation)
        """
        if self.gemini_client is None and self.gemini_model is None:
            return False, ""
        
        prompt = f"""Analyze this text for subtle Kenyan political incitement or hate speech.

Look specifically for:
1. Ethnic metaphors like "kwekwe", "madoadoa" (spots/stains), "kama mende" (like cockroaches)
2. Coded political language that implies ethnic targeting
3. Subtle calls for violence or ethnic exclusion
4. Delegitimizing language about certain communities being "foreigners" or "not belonging"
5. Historical references to past ethnic violence

Text to analyze: "{text}"

Respond with ONLY a JSON object:
{{"flagged": true/false, "reason": "brief explanation or empty string"}}

If the text is benign, respond with: {{"flagged": false, "reason": ""}}
"""
        
        try:
            if GENAI_NEW_API and self.gemini_client:
                # New API (google.genai) - uses client.generate_content
                try:
                    # Try async method first
                    response = await self.gemini_client.models.generate_content_async(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    result_text = response.text.strip()
                except AttributeError:
                    # Fallback to sync method if async not available
                    response = self.gemini_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    result_text = response.text.strip()
            elif self.gemini_model:
                # Deprecated API (google.generativeai)
                response = await self.gemini_model.generate_content_async(prompt)
                result_text = response.text.strip()
            else:
                return False, ""
            
            # Parse the JSON response
            import json
            # Handle potential markdown code blocks
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            return result.get("flagged", False), result.get("reason", "")
            
        except Exception as e:
            print(f"Error in Gemini context check: {e}")
            return False, ""
    
    async def _translate_message(self, message: str, target_language: str) -> str:
        """
        Translate a message using Gemini.
        
        Args:
            message: The message to translate
            target_language: Target language (e.g., "Swahili", "Sheng")
            
        Returns:
            Translated message
        """
        if self.gemini_client is None and self.gemini_model is None:
            return message  # Return original if Gemini not available
        
        prompt = f"""Translate the following message to {target_language}.
Keep the tone informative and helpful. This is a message warning about potentially harmful content.

Message: "{message}"

Respond with ONLY the translated text, nothing else."""
        
        try:
            if GENAI_NEW_API and self.gemini_client:
                # New API (google.genai) - uses client.generate_content
                try:
                    # Try async method first
                    response = await self.gemini_client.models.generate_content_async(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    return response.text.strip()
                except AttributeError:
                    # Fallback to sync method if async not available
                    response = self.gemini_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    return response.text.strip()
            elif self.gemini_model:
                # Deprecated API (google.generativeai)
                response = await self.gemini_model.generate_content_async(prompt)
                return response.text.strip()
            else:
                return message
        except Exception as e:
            print(f"Error in translation: {e}")
            return message
    
    def _build_explanation(
        self,
        risk_level: str,
        matched_keyword: Optional[str],
        gemini_context_flag: bool,
        scores: Dict[str, float],
    ) -> str:
        """Build a short human-readable explanation for the risk level."""
        parts = []
        if matched_keyword:
            parts.append(f"Matched lexicon keyword: {matched_keyword}")
        if gemini_context_flag:
            parts.append("Gemini flagged Kenyan political context (hate/incitement risk)")
        if scores and "toxicity" in scores:
            t = scores.get("toxicity", 0)
            if t >= 0.7:
                parts.append(f"High toxicity score: {t:.2f}")
            elif t >= 0.4:
                parts.append(f"Moderate toxicity score: {t:.2f}")
        if not parts:
            if risk_level == "HIGH":
                parts.append("Combined signals indicated high risk")
            elif risk_level == "MEDIUM":
                parts.append("Combined signals indicated moderate risk")
            else:
                parts.append("No harmful signals detected")
        return " | ".join(parts)

    def _generate_response_message(self, risk_level: str, matched_keyword: Optional[str] = None) -> str:
        """
        Generate a human-friendly response message in English.
        
        Args:
            risk_level: The determined risk level
            matched_keyword: Any matched lexicon keyword
            
        Returns:
            Response message in English
        """
        if risk_level == "HIGH":
            if matched_keyword:
                context = get_keyword_context(matched_keyword)
                return f"Warning: This message contains harmful content. {context} Please verify information from official sources before sharing."
            return "Warning: This message contains potentially harmful content including hate speech or incitement. Please verify information from official sources before sharing."
        
        elif risk_level == "MEDIUM":
            return "Caution: This message may contain misleading or inflammatory content. We recommend verifying with official sources before sharing."
        
        else:  # LOW
            return "This message appears to be safe. However, always verify important claims from official sources."
    
    async def analyze(self, text: str, sector: str = "political") -> AnalysisResult:
        """
        Analyze text for toxicity and return a comprehensive result.

        Pipeline:
        1. Sector-specific lexicon check
        2. Detoxify toxicity scores
        2.5. Kenyan fine-tuned classifier (if model artifact present)
        3. Gemini (or Ollama fallback) context check
        4. Weighted ensemble → final risk + confidence
        5. Translation to English, Swahili, Sheng
        """
        # ---- Step 1: Lexicon ----
        is_flagged, matched_keyword, lexicon_risk = check_lexicon(text, sector=sector)
        lexicon_conf = 1.0 if lexicon_risk == "HIGH" else (0.7 if lexicon_risk == "MEDIUM" else 0.0)

        # ---- Step 2: Detoxify ----
        scores = self._get_detoxify_scores(text)
        max_score = self._get_max_toxicity_score(scores)
        detoxify_risk = self._map_score_to_risk(max_score)

        # ---- Step 2.5: Kenyan classifier ----
        kenyan_result = kenyan_classifier.predict(text)
        kenyan_risk = kenyan_result[0] if kenyan_result else None
        kenyan_conf = kenyan_result[1] if kenyan_result else 0.0

        # ---- Step 3: Gemini context (with circuit breaker & Ollama fallback) ----
        gemini_flagged = False
        if self._gemini_available():
            try:
                gemini_flagged, _ = await self._check_kenyan_context(text)
                self._record_gemini_success()
            except Exception as e:
                print(f"Gemini context check failed: {e}")
                self._record_gemini_failure()
                ollama_resp = await self._call_ollama(
                    f'Is this Kenyan political incitement? Answer JSON {{"flagged":true/false}}: "{text[:500]}"'
                )
                if ollama_resp and '"flagged": true' in ollama_resp.lower().replace(" ", ""):
                    gemini_flagged = True
        elif _LOCAL_LLM_ENABLED:
            ollama_resp = await self._call_ollama(
                f'Is this Kenyan political incitement? Answer JSON {{"flagged":true/false}}: "{text[:500]}"'
            )
            if ollama_resp and '"flagged": true' in ollama_resp.lower().replace(" ", ""):
                gemini_flagged = True

        gemini_conf = 0.9 if gemini_flagged else 0.0

        # ---- Step 4: Ensemble ----
        votes = {
            "lexicon": lexicon_conf,
            "detoxify": max_score,
            "kenyan_model": kenyan_conf,
            "gemini": gemini_conf,
        }
        confidence = (
            _W_LEXICON * lexicon_conf
            + _W_DETOXIFY * max_score
            + _W_KENYAN * kenyan_conf
            + _W_GEMINI * gemini_conf
        )
        confidence = min(1.0, confidence)

        # Determine final risk from ensemble
        risk_level = "LOW"
        if (
            lexicon_risk == "HIGH"
            or detoxify_risk == "HIGH"
            or kenyan_risk == "HIGH"
            or gemini_flagged
        ):
            risk_level = "HIGH"
        elif (
            lexicon_risk == "MEDIUM"
            or detoxify_risk == "MEDIUM"
            or kenyan_risk == "MEDIUM"
        ):
            risk_level = "MEDIUM"

        # ---- Step 5: Messages ----
        english_msg = self._generate_response_message(risk_level, matched_keyword)
        messages = {"english": english_msg}

        translated = False
        if self._gemini_available():
            try:
                messages["swahili"] = await self._translate_message(english_msg, "Swahili")
                messages["sheng"] = await self._translate_message(english_msg, "Sheng (Kenyan urban slang)")
                translated = True
                self._record_gemini_success()
            except Exception:
                self._record_gemini_failure()

        if not translated and _LOCAL_LLM_ENABLED:
            sw = await self._call_ollama(f"Translate to Swahili: {english_msg}")
            sh = await self._call_ollama(f"Translate to Kenyan Sheng: {english_msg}")
            messages["swahili"] = sw or english_msg
            messages["sheng"] = sh or english_msg
            translated = True

        if not translated:
            if risk_level == "HIGH":
                messages["swahili"] = "Onyo: Ujumbe huu una maudhui hatari yanayoweza kuchochea chuki. Tafadhali hakiki habari kutoka vyanzo rasmi."
                messages["sheng"] = "Heads up: Message iko na vitu mbaya sana. Confirm kwanza na official sources kabla ya ku-share."
            elif risk_level == "MEDIUM":
                messages["swahili"] = "Tahadhari: Ujumbe huu unaweza kuwa na maudhui yanayopotosha. Hakiki na vyanzo rasmi."
                messages["sheng"] = "Be careful: Message hii inaweza kuwa na mambo ya kupotosha. Check na official sources."
            else:
                messages["swahili"] = "Ujumbe huu unaonekana salama. Hata hivyo, hakiki madai muhimu kutoka vyanzo rasmi."
                messages["sheng"] = "Message inaonekana poa. Lakini bado confirm important stuff na official sources."

        explanation_details = {
            "lexicon": {"keyword": matched_keyword, "risk": lexicon_risk, "confidence": lexicon_conf},
            "detoxify": {"max_score": round(max_score, 3), "risk": detoxify_risk},
            "kenyan_model": {"risk": kenyan_risk, "confidence": round(kenyan_conf, 3)} if kenyan_result else None,
            "gemini": {"flagged": gemini_flagged, "confidence": gemini_conf},
            "final_confidence": round(confidence, 3),
        }

        return AnalysisResult(
            risk_level=risk_level,
            scores=scores,
            messages=messages,
            matched_keyword=matched_keyword,
            gemini_context_flag=gemini_flagged,
            explanation=self._build_explanation(risk_level, matched_keyword, gemini_flagged, scores),
            confidence_score=round(confidence, 3),
            kenyan_model_risk=kenyan_risk,
            kenyan_model_score=round(kenyan_conf, 3) if kenyan_result else None,
            explanation_details=explanation_details,
        )
    
    def analyze_sync(self, text: str) -> AnalysisResult:
        """
        Synchronous version of analyze for non-async contexts.
        
        Note: This version skips Gemini translation and context checking.
        Use the async version for full functionality.
        """
        # Check lexicon first
        is_flagged, matched_keyword, lexicon_risk = check_lexicon(text)
        
        if is_flagged and lexicon_risk == "HIGH":
            english_msg = self._generate_response_message("HIGH", matched_keyword)
            return AnalysisResult(
                risk_level="HIGH",
                scores={"lexicon_match": 1.0},
                messages={
                    "english": english_msg,
                    "swahili": "Onyo: Ujumbe huu una maudhui hatari.",
                    "sheng": "Heads up: Message iko na vitu mbaya sana."
                },
                matched_keyword=matched_keyword,
                explanation=self._build_explanation("HIGH", matched_keyword, False, {"lexicon_match": 1.0}),
            )
        
        # Get Detoxify scores
        scores = self._get_detoxify_scores(text)
        max_score = self._get_max_toxicity_score(scores)
        risk_level = self._map_score_to_risk(max_score)
        
        # Consider lexicon medium risk
        if is_flagged and lexicon_risk == "MEDIUM" and risk_level == "LOW":
            risk_level = "MEDIUM"
        
        english_msg = self._generate_response_message(risk_level, matched_keyword)
        
        # Fallback translations
        if risk_level == "HIGH":
            swahili = "Onyo: Ujumbe huu una maudhui hatari yanayoweza kuchochea chuki."
            sheng = "Heads up: Message iko na vitu mbaya sana."
        elif risk_level == "MEDIUM":
            swahili = "Tahadhari: Ujumbe huu unaweza kuwa na maudhui yanayopotosha."
            sheng = "Be careful: Message hii inaweza kuwa na mambo ya kupotosha."
        else:
            swahili = "Ujumbe huu unaonekana salama."
            sheng = "Message inaonekana poa."
        
        return AnalysisResult(
            risk_level=risk_level,
            scores=scores,
            messages={
                "english": english_msg,
                "swahili": swahili,
                "sheng": sheng
            },
            matched_keyword=matched_keyword,
            explanation=self._build_explanation(risk_level, matched_keyword, False, scores),
        )


# Singleton instance for reuse
_analyzer_instance: Optional[MwavuliAnalyzer] = None


def get_analyzer() -> MwavuliAnalyzer:
    """Get or create the singleton analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        try:
            _analyzer_instance = MwavuliAnalyzer()
        except Exception as e:
            print(f"Warning: Failed to initialize analyzer: {e}")
            # Still create instance, but it will use fallback behavior
            _analyzer_instance = MwavuliAnalyzer()
    return _analyzer_instance

