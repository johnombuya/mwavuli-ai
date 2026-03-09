"""
Mwavuli Lexicon - Multi-sector keyword detection.

Supports sector-specific keyword sets stored in ``backend/lexicons/``.
The default sector is ``political`` (original Mwavuli keywords).
"""

import csv
import importlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Sector registry — lazy-loaded from backend/lexicons/<sector>.py
# ---------------------------------------------------------------------------
_VALID_SECTORS = ("political", "health", "security", "fraud")

_sector_cache: Dict[str, Dict[str, List[str]]] = {}


def _load_sector(sector: str) -> Dict[str, List[str]]:
    """Import a sector module and return its HIGH/MEDIUM keyword lists."""
    if sector in _sector_cache:
        return _sector_cache[sector]
    try:
        mod = importlib.import_module(f"lexicons.{sector}")
        data = {
            "high": list(getattr(mod, "HIGH_RISK_KEYWORDS", [])),
            "medium": list(getattr(mod, "MEDIUM_RISK_KEYWORDS", [])),
            "contexts": dict(getattr(mod, "KEYWORD_CONTEXTS", {})),
        }
    except ModuleNotFoundError:
        data = {"high": [], "medium": [], "contexts": {}}
    _sector_cache[sector] = data
    return data


# Backward-compat aliases (used by CSV extension and existing imports)
_political = _load_sector("political")
HIGH_RISK_KEYWORDS = _political["high"]
MEDIUM_RISK_KEYWORDS = _political["medium"]


def check_lexicon(
    text: str,
    sector: str = "political",
) -> Tuple[bool, Optional[str], str]:
    """
    Check text against a sector-specific keyword lexicon.

    Args:
        text:   The text to analyze.
        sector: One of ``political``, ``health``, ``security``, ``fraud``.

    Returns:
        ``(is_flagged, matched_keyword, risk_level)``
    """
    data = _load_sector(sector)
    text_lower = text.lower()

    for keyword in data["high"]:
        if keyword.lower() in text_lower:
            return (True, keyword, "HIGH")

    for keyword in data["medium"]:
        if keyword.lower() in text_lower:
            return (True, keyword, "MEDIUM")

    return (False, None, "NONE")


def get_keyword_context(keyword: str, sector: str = "political") -> str:
    """Return contextual explanation for a flagged keyword."""
    data = _load_sector(sector)
    return data["contexts"].get(
        keyword.lower(),
        "This term has been flagged as potentially harmful.",
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
