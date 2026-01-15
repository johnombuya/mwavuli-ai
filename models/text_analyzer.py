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

# Load environment variables
load_dotenv()

# Pre-bunking tip for all responses
PREBUNKING_TIP = "For official election results, always visit iebc.or.ke"


@dataclass
class AnalysisResult:
    """Result of text analysis."""
    risk_level: str  # HIGH, MEDIUM, LOW
    scores: Dict[str, float]  # Raw toxicity scores
    messages: Dict[str, str]  # Translated messages
    matched_keyword: Optional[str] = None
    gemini_context_flag: bool = False
    prebunking_tip: str = PREBUNKING_TIP


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
        # This prevents startup failures if model download is corrupted
        self.detoxify_model = None
        self._detoxify_loading = False
        self._detoxify_error = None
        
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
    
    async def analyze(self, text: str) -> AnalysisResult:
        """
        Analyze text for toxicity and return a comprehensive result.
        
        This method:
        1. First checks the lexicon for immediate high-risk keywords
        2. Gets Detoxify toxicity scores
        3. Uses Gemini for Kenyan context checking
        4. Generates translated responses in English, Swahili, and Sheng
        
        Args:
            text: The text to analyze
            
        Returns:
            AnalysisResult with risk level, scores, and translated messages
        """
        # Step 1: Check lexicon first (bypass model if high-risk keyword found)
        is_flagged, matched_keyword, lexicon_risk = check_lexicon(text)
        
        if is_flagged and lexicon_risk == "HIGH":
            # Immediate HIGH risk - bypass model scoring
            english_msg = self._generate_response_message("HIGH", matched_keyword)
            
            messages = {"english": english_msg}
            
            # Still try to translate if Gemini is available
            if self.gemini_client or self.gemini_model:
                try:
                    messages["swahili"] = await self._translate_message(english_msg, "Swahili")
                    messages["sheng"] = await self._translate_message(english_msg, "Sheng (Kenyan urban slang)")
                except Exception:
                    messages["swahili"] = english_msg
                    messages["sheng"] = english_msg
            else:
                messages["swahili"] = english_msg
                messages["sheng"] = english_msg
            
            return AnalysisResult(
                risk_level="HIGH",
                scores={"lexicon_match": 1.0},
                messages=messages,
                matched_keyword=matched_keyword,
                gemini_context_flag=False
            )
        
        # Step 2: Get Detoxify scores
        scores = self._get_detoxify_scores(text)
        max_score = self._get_max_toxicity_score(scores)
        risk_level = self._map_score_to_risk(max_score)
        
        # Step 3: Gemini context check for subtle incitement
        gemini_flagged = False
        if self.gemini_client or self.gemini_model:
            try:
                gemini_flagged, gemini_reason = await self._check_kenyan_context(text)
                if gemini_flagged:
                    risk_level = "HIGH"  # Upgrade to HIGH if Gemini flags it
            except Exception as e:
                print(f"Gemini context check failed: {e}")
        
        # Consider lexicon medium risk
        if is_flagged and lexicon_risk == "MEDIUM" and risk_level == "LOW":
            risk_level = "MEDIUM"
        
        # Step 4: Generate response messages
        english_msg = self._generate_response_message(risk_level, matched_keyword)
        
        messages = {"english": english_msg}
        
        # Translate messages
        if self.gemini_client or self.gemini_model:
            try:
                messages["swahili"] = await self._translate_message(english_msg, "Swahili")
                messages["sheng"] = await self._translate_message(english_msg, "Sheng (Kenyan urban slang)")
            except Exception:
                messages["swahili"] = english_msg
                messages["sheng"] = english_msg
        else:
            # Fallback translations when Gemini is not available
            if risk_level == "HIGH":
                messages["swahili"] = "Onyo: Ujumbe huu una maudhui hatari yanayoweza kuchochea chuki. Tafadhali hakiki habari kutoka vyanzo rasmi."
                messages["sheng"] = "Heads up: Message iko na vitu mbaya sana. Confirm kwanza na official sources kabla ya ku-share."
            elif risk_level == "MEDIUM":
                messages["swahili"] = "Tahadhari: Ujumbe huu unaweza kuwa na maudhui yanayopotosha. Hakiki na vyanzo rasmi."
                messages["sheng"] = "Be careful: Message hii inaweza kuwa na mambo ya kupotosha. Check na official sources."
            else:
                messages["swahili"] = "Ujumbe huu unaonekana salama. Hata hivyo, hakiki madai muhimu kutoka vyanzo rasmi."
                messages["sheng"] = "Message inaonekana poa. Lakini bado confirm important stuff na official sources."
        
        return AnalysisResult(
            risk_level=risk_level,
            scores=scores,
            messages=messages,
            matched_keyword=matched_keyword,
            gemini_context_flag=gemini_flagged
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
                matched_keyword=matched_keyword
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
            matched_keyword=matched_keyword
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

