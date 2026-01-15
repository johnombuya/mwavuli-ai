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

from typing import Optional, Tuple


# High-risk keywords specific to Kenyan political context
# These terms have historically been associated with ethnic incitement
HIGH_RISK_KEYWORDS = [
    # Ethnic metaphors used in past violence
    "kwekwe",           # Derogatory term, associated with 2007 violence
    "madoadoa",         # "Spots" - coded term for ethnic minorities
    "kama mende",       # "Like cockroaches" - dehumanizing language
    "wageni",           # "Foreigners" - used to delegitimize citizens
    "wabara",           # Derogatory term for inland communities
    "wahamiaji",        # "Immigrants" - used as ethnic slur
    
    # Political incitement phrases
    "funga debe",       # "Close the tin" - election manipulation
    "piga debe",        # Related to ballot stuffing
    "no raila no peace", # Incitement phrase
    "41 vs 1",          # Ethnic coalition framing
    "kura yangu",       # Can be used in incitement context
    
    # Violent language
    "songa mbele",      # "Move forward" - can be violence incitement
    "toeni",            # "Remove them" - ethnic cleansing language
    "wafukuze",         # "Chase them away"
    "wachinje",         # Explicit violence
    "ondoeni",          # "Remove" - often ethnic targeting
    
    # Coded political terms
    "uthamaki",         # Ethnic supremacy ideology
    "mlevi",            # "Drunkard" - coded political insult
    "mganga",           # "Witch doctor" - coded political attack
    "wezi",             # "Thieves" - can incite violence against groups
    
    # Incitement slogans
    "hatupangwingwi",   # Political slogan that can be used aggressively
    "baba tosha",       # Context-dependent political phrase
    "tuko pamoja",      # Can be used for ethnic solidarity incitement
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
    
    return contexts.get(keyword.lower(), "This term has been flagged as potentially harmful in the Kenyan political context.")

