"""
Mwavuli Lexicon - Kenya-specific high-risk political keywords.

This module provides manual overrides for region-specific political terms
that standard toxicity models might miss. These terms are checked BEFORE
model inference - if a keyword is found, the risk level is immediately
set to HIGH.

Context: During Kenyan elections, certain coded language and metaphors
have historically been used to incite ethnic violence. This lexicon
helps catch such terms that AI models trained on Western data may miss.
"""

import csv
import os
from pathlib import Path
from typing import Optional, Tuple


# High-risk keywords specific to Kenyan political context
# These terms have historically been associated with ethnic incitement
HIGH_RISK_KEYWORDS = [
    # Ethnic metaphors used in past violence
    "kwekwe",  # Derogatory term, associated with 2007 violence
    "madoadoa",  # "Spots" - coded term for ethnic minorities
    "kama mende",  # "Like cockroaches" - dehumanizing language
    "wageni",  # "Foreigners" - used to delegitimize citizens
    "wabara",  # Derogatory term for inland communities
    "wahamiaji",  # "Immigrants" - used as ethnic slur
    # Political incitement phrases
    "funga debe",  # "Close the tin" - election manipulation
    "piga debe",  # Related to ballot stuffing
    "no raila no peace",  # Incitement phrase
    "41 vs 1",  # Ethnic coalition framing
    "kura yangu",  # Can be used in incitement context
    # Violent language
    "songa mbele",  # "Move forward" - can be violence incitement
    "toeni",  # "Remove them" - ethnic cleansing language
    "wafukuze",  # "Chase them away"
    "wachinje",  # Explicit violence
    "ondoeni",  # "Remove" - often ethnic targeting
    # Coded political terms
    "uthamaki",  # Ethnic supremacy ideology
    "mlevi",  # "Drunkard" - coded political insult
    "mganga",  # "Witch doctor" - coded political attack
    "wezi",  # "Thieves" - can incite violence against groups
    # Incitement slogans
    "hatupangwingwi",  # Political slogan that can be used aggressively
    "baba tosha",  # Context-dependent political phrase
    "tuko pamoja",  # Can be used for ethnic solidarity incitement
    # Additional high-risk terms from lexicon CSV
    "fumigation",
    "uncircumcised",
    "eliminate",
    "kill",
    "wabara waende kwao",
    "kaffir",
    "mende",
    "kihii",
    "kimurkeldet",
    "otutu labotonik",
    "sangara",
    "bunyot",
    "wakuja",
    "chinja kafir",
    "brown teeth",
    "kalenjin weti",
    "orm",
    "mandera militant",
    "garissa gun",
    "laikipia rancher foe",
    "panga squad",
    "kamba assassins",
]

# Medium-risk keywords - flag for additional context check
MEDIUM_RISK_KEYWORDS = [
    "uchaguzi",         # "Election" - context dependent
    "vita",             # "War" - needs context
    "mapambano",        # "Struggle" - context dependent
    "unga",             # Economic grievance term
    "mwizi",            # "Thief" - political accusation
    "mkora",            # "Crook" - political insult
    "tumerudishwa",     # Grievance language
    # Additional medium-risk terms from lexicon CSV
    "chunga kura",
    "watajua hawajui",
    "kama noma noma",
    "operation linda kura",
    "uthamaki ni witu",
    "ngetiik",
    "maharagwe",
    "sipangwingwi",
    "kama mbaya mbaya",
    "watu wa kurusha mawe",
    "secure the vote",
    "mabesha",
    "mzungu mdogo",
    "kamba machete",
    "turkana ak-47",
    "masai morans",
    "borana well",
    "nyanza witch",
    "rift valley cow",
    "ukambani snake",
    "kisumu stone",
    "nakuru hyena",
    "mombasa pirate",
    "kericho tea thief",
    "rungu wielder",
    "arrow boys",
    "kalenjin warriors",
    "luo youth",
    "kikuyu goons",
    "wajir camel jockey",
]


def check_lexicon(text: str) -> Tuple[bool, Optional[str], str]:
    """
    Check if text contains high-risk Kenyan political keywords.
    
    This check runs BEFORE model inference. If a high-risk keyword is found,
    we immediately return HIGH risk without running the AI model.
    
    Args:
        text: The text to analyze
        
    Returns:
        Tuple of (is_flagged, matched_keyword, risk_level)
        - is_flagged: True if a keyword was found
        - matched_keyword: The keyword that was matched (or None)
        - risk_level: "HIGH", "MEDIUM", or "NONE"
    """
    text_lower = text.lower()
    
    # Check high-risk keywords first
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword.lower() in text_lower:
            return (True, keyword, "HIGH")
    
    # Check medium-risk keywords
    for keyword in MEDIUM_RISK_KEYWORDS:
        if keyword.lower() in text_lower:
            return (True, keyword, "MEDIUM")
    
    return (False, None, "NONE")


def get_keyword_context(keyword: str) -> str:
    """
    Get contextual information about why a keyword is flagged.
    
    Args:
        keyword: The matched keyword
        
    Returns:
        A string explaining the keyword's significance
    """
    contexts = {
        "madoadoa": "This term means 'spots' and has been used historically to refer to ethnic minorities as 'stains' that need to be 'cleaned' from an area.",
        "kwekwe": "A derogatory term that was associated with ethnic violence during the 2007-2008 post-election crisis.",
        "41 vs 1": "Framing that suggests ethnic coalition building against a single community.",
        "wachinje": "Explicit call for violence.",
        "toeni": "Removal language often used in context of ethnic cleansing.",
    }
    
    return contexts.get(
        keyword.lower(),
        (
            "This term has been flagged as potentially harmful in the "
            "Kenyan political context."
        ),
    )


def _default_csv_path() -> Path:
    """
    Compute default path to the optional lexicon CSV at repo root.
    """
    root = Path(__file__).resolve().parents[2]
    return root / (
        "term-language-literalmeaning-impliedmeaningcontext-"
        "category-risklevelguess-exampleusageparaphrased-"
        "notesformoderators.csv"
    )


def _extend_keywords_from_csv() -> None:
    """
    Optionally extend HIGH/MEDIUM keyword lists from a CSV file.
    
    The CSV is expected to have columns:
    term, language, literal_meaning, implied_meaning_context,
    category, risk_level_guess, example_usage_paraphrased,
    notes_for_moderators.
    
    Only rows with risk_level_guess of HIGH or MEDIUM are used.
    """
    csv_env = os.getenv("MWAVULI_LEXICON_CSV_PATH")
    path = Path(csv_env) if csv_env else _default_csv_path()
    if not path.exists():
        return

    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                term = (row.get("term") or "").strip()
                level = (row.get("risk_level_guess") or "").strip().upper()
                if not term or level not in {"HIGH", "MEDIUM"}:
                    continue
                if level == "HIGH":
                    if term not in HIGH_RISK_KEYWORDS:
                        HIGH_RISK_KEYWORDS.append(term)
                else:
                    if term not in MEDIUM_RISK_KEYWORDS:
                        MEDIUM_RISK_KEYWORDS.append(term)
    except Exception:
        # Fail safely: keep the built-in lexicon only
        return


_extend_keywords_from_csv()

