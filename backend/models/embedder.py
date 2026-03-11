"""
Text embedding utility using sentence-transformers.

Provides 384-dimensional embeddings via paraphrase-multilingual-MiniLM-L12-v2,
which supports 50+ languages including English and Swahili.

If sentence-transformers is not installed, all functions return None so
the rest of the pipeline keeps working.
"""

from typing import List, Optional

_model = None
_loaded = False

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384


def _ensure_loaded() -> bool:
    global _model, _loaded
    if _loaded:
        return _model is not None
    _loaded = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
        print(f"[embedder] Model loaded: {MODEL_NAME}")
        return True
    except ImportError:
        print("[embedder] sentence-transformers not installed — embeddings disabled.")
        return False
    except Exception as e:
        print(f"[embedder] Could not load model: {e}")
        return False


def embed(text: str) -> Optional[List[float]]:
    """
    Return a 384-dim embedding for *text*, or None if unavailable.
    """
    if not _ensure_loaded():
        return None
    try:
        vec = _model.encode(text, show_progress_bar=False)
        return vec.tolist()
    except Exception as e:
        print(f"[embedder] Encoding error: {e}")
        return None


def embed_batch(texts: List[str], batch_size: int = 64) -> List[Optional[List[float]]]:
    """
    Embed multiple texts efficiently. Returns a list parallel to *texts*;
    entries are None if the model is unavailable.
    """
    if not _ensure_loaded():
        return [None] * len(texts)
    try:
        vecs = _model.encode(texts, batch_size=batch_size, show_progress_bar=True)
        return [v.tolist() for v in vecs]
    except Exception as e:
        print(f"[embedder] Batch encoding error: {e}")
        return [None] * len(texts)
