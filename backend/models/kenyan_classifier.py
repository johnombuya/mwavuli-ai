"""
Fine-tuned Kenyan risk classifier.

Loads a DistilBERT/XLM-R checkpoint trained on Kenyan political text
and returns a risk label + confidence score.

Loading priority:
1. HuggingFace Hub  -- if HF_MODEL_REPO env var is set
2. Local artifacts  -- backend/models/artifacts/kenyan_classifier/
3. Graceful skip    -- returns None so the rest of the pipeline continues
"""

import os
from pathlib import Path
from typing import Optional, Tuple

_MODEL_DIR = (
    Path(__file__).resolve().parent / "artifacts" / "kenyan_classifier"
)

_model = None
_tokenizer = None
_labels = ["LOW", "MEDIUM", "HIGH"]
_loaded = False


def _ensure_loaded() -> bool:
    global _model, _tokenizer, _loaded
    if _loaded:
        return _model is not None
    _loaded = True

    hf_repo = os.getenv("HF_MODEL_REPO", "").strip()
    hf_token = os.getenv("HF_TOKEN", "").strip() or None

    try:
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        if hf_repo:
            try:
                _tokenizer = AutoTokenizer.from_pretrained(hf_repo, token=hf_token)
                _model = AutoModelForSequenceClassification.from_pretrained(
                    hf_repo, token=hf_token,
                )
                _model.eval()
                print(f"[kenyan_classifier] Model loaded from Hub: {hf_repo}")
                return True
            except Exception as e:
                print(f"[kenyan_classifier] Hub load failed ({e}), trying local...")

        if _MODEL_DIR.exists():
            _tokenizer = AutoTokenizer.from_pretrained(str(_MODEL_DIR))
            _model = AutoModelForSequenceClassification.from_pretrained(
                str(_MODEL_DIR),
            )
            _model.eval()
            print("[kenyan_classifier] Model loaded from", _MODEL_DIR)
            return True

        return False
    except Exception as e:
        print(f"[kenyan_classifier] Could not load model: {e}")
        return False


def predict(text: str) -> Optional[Tuple[str, float]]:
    """
    Predict risk level for *text*.

    Returns ``(risk_label, confidence)`` or ``None`` if the model is
    not available.
    """
    if not _ensure_loaded():
        return None
    try:
        import torch
        inputs = _tokenizer(
            text, return_tensors="pt",
            truncation=True, max_length=512,
        )
        with torch.no_grad():
            logits = _model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        idx = int(probs.argmax())
        return _labels[idx], float(probs[idx])
    except Exception as e:
        print(f"[kenyan_classifier] Prediction error: {e}")
        return None
