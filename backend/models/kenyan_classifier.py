"""
Fine-tuned Kenyan risk classifier.

Loads a locally-saved DistilBERT/XLM-R checkpoint trained on Kenyan
political text and returns a risk label + confidence score.

Model artifact directory: backend/models/artifacts/kenyan_classifier/
If the artifact is absent the classifier silently returns None so that
the rest of the pipeline continues.
"""

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
    if not _MODEL_DIR.exists():
        return False
    try:
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )
        _tokenizer = AutoTokenizer.from_pretrained(str(_MODEL_DIR))
        _model = AutoModelForSequenceClassification.from_pretrained(
            str(_MODEL_DIR),
        )
        _model.eval()
        print("[kenyan_classifier] Model loaded from", _MODEL_DIR)
        return True
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
