"""
Train a fine-tuned Kenyan risk classifier.

Usage:
  python scripts/train_kenyan_classifier.py [--epochs 3] [--model distilbert-base-multilingual-cased]

Steps:
1. Export labeled data from Supabase (text + risk_level).
   Falls back to Firestore if DB_PROVIDER=firebase.
2. Optionally augment with a local CSV (e.g. HateSpeech_Kenya.csv).
3. Fine-tune a small transformer on 3-class classification (LOW/MEDIUM/HIGH).
4. Evaluate with per-class precision, recall, and F1.
5. Save to backend/models/artifacts/kenyan_classifier/
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv
load_dotenv(_backend_root / ".env")

ARTIFACT_DIR = _backend_root / "models" / "artifacts" / "kenyan_classifier"
LABEL_MAP = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
LABEL_NAMES = ["LOW", "MEDIUM", "HIGH"]

# Kaggle hatespeech-kenya uses: 0=hate_speech, 1=offensive, 2=neither
KAGGLE_CLASS_MAP = {0: 2, 1: 1, 2: 0}  # hate->HIGH, offensive->MEDIUM, neither->LOW


def _load_supabase_data() -> pd.DataFrame:
    """Pull labeled reports from Supabase."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("Supabase not configured — skipping.")
        return pd.DataFrame(columns=["text", "label"])
    try:
        from supabase import create_client
        client = create_client(url, key)
    except Exception as e:
        print(f"Supabase client error: {e} — skipping.")
        return pd.DataFrame(columns=["text", "label"])

    rows = []
    offset = 0
    batch = 1000
    while True:
        result = (
            client.table("reports")
            .select("text, risk_level")
            .in_("risk_level", ["LOW", "MEDIUM", "HIGH"])
            .range(offset, offset + batch - 1)
            .execute()
        )
        for r in (result.data or []):
            text = (r.get("text") or "").strip()
            risk = r.get("risk_level", "").upper()
            if text and risk in LABEL_MAP:
                rows.append({"text": text, "label": LABEL_MAP[risk]})
        if len(result.data or []) < batch:
            break
        offset += batch

    print(f"Loaded {len(rows)} rows from Supabase.")
    return pd.DataFrame(rows)


def _load_firestore_data() -> pd.DataFrame:
    """Pull labeled reports from Firestore (legacy fallback)."""
    try:
        from utils.db import _get_db
        db = _get_db()
    except Exception:
        db = None
    if db is None:
        print("Firestore not available — skipping.")
        return pd.DataFrame(columns=["text", "label"])
    ref = (
        db.collection("artifacts")
        .document("mwavuli")
        .collection("public")
        .document("data")
        .collection("reports")
    )
    rows = []
    for doc in ref.stream():
        d = doc.to_dict()
        text = d.get("text", "").strip()
        risk = d.get("risk_level", "").upper()
        if text and risk in LABEL_MAP:
            rows.append({"text": text, "label": LABEL_MAP[risk]})
    print(f"Loaded {len(rows)} rows from Firestore.")
    return pd.DataFrame(rows)


def _load_db_data() -> pd.DataFrame:
    """Load from whichever DB provider is configured."""
    provider = os.getenv("DB_PROVIDER", "supabase").lower()
    if provider == "firebase":
        return _load_firestore_data()
    return _load_supabase_data()


def _load_csv_data(csv_path: str) -> pd.DataFrame:
    """Load supplementary CSV. Auto-detects Kaggle hatespeech-kenya format."""
    if not csv_path or not Path(csv_path).exists():
        return pd.DataFrame(columns=["text", "label"])
    df = pd.read_csv(csv_path, on_bad_lines="skip")
    text_col = next(
        (c for c in df.columns if c.lower() in ("tweet", "text", "message")),
        df.columns[0],
    )

    # Auto-detect Kaggle hatespeech-kenya by its characteristic "Class" column
    if "Class" in df.columns and all(
        c in df.columns for c in ("hate_speech", "offensive_language", "neither")
    ):
        print("Detected Kaggle hatespeech-kenya format — mapping Class column.")
        rows = []
        for _, row in df.iterrows():
            text = str(row[text_col]).strip()
            cls = row["Class"]
            if pd.isna(cls) or not text:
                continue
            label = KAGGLE_CLASS_MAP.get(int(cls))
            if label is not None:
                rows.append({"text": text, "label": label})
        print(f"Loaded {len(rows)} rows from Kaggle CSV.")
        return pd.DataFrame(rows)

    # Generic CSV with a label/risk column
    label_col = next(
        (c for c in df.columns if "label" in c.lower() or "risk" in c.lower()), None
    )
    if label_col is None:
        print(f"No label column found in {csv_path}")
        return pd.DataFrame(columns=["text", "label"])
    rows = []
    for _, row in df.iterrows():
        text = str(row[text_col]).strip()
        raw = str(row[label_col]).strip().upper()
        label = LABEL_MAP.get(raw)
        if label is None:
            try:
                label = int(raw)
            except ValueError:
                continue
        if text:
            rows.append({"text": text, "label": label})
    print(f"Loaded {len(rows)} rows from CSV.")
    return pd.DataFrame(rows)


def _compute_metrics(eval_pred):
    """HuggingFace Trainer-compatible metric function."""
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support

    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    acc = accuracy_score(labels, preds)
    prec, rec, f1, _ = precision_recall_fscore_support(
        labels, preds, average="weighted", zero_division=0
    )
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1}


def train(base_model: str, epochs: int, csv_path: str) -> None:
    from datasets import Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    df = pd.concat([_load_db_data(), _load_csv_data(csv_path)], ignore_index=True)
    df = df.drop_duplicates(subset=["text"]).reset_index(drop=True)

    print(f"\nTotal training samples: {len(df)}")
    print("Label distribution:")
    for name, idx in LABEL_MAP.items():
        count = (df["label"] == idx).sum()
        print(f"  {name}: {count} ({count / len(df) * 100:.1f}%)")

    if len(df) < 20:
        print(f"Only {len(df)} samples — too few to train. Aborting.")
        return

    ds = Dataset.from_pandas(df)
    ds = ds.train_test_split(test_size=0.15, seed=42)

    tokenizer = AutoTokenizer.from_pretrained(base_model)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=256, padding="max_length")

    ds = ds.map(tokenize, batched=True)
    ds = ds.rename_column("label", "labels")
    ds.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

    model = AutoModelForSequenceClassification.from_pretrained(base_model, num_labels=3)

    args = TrainingArguments(
        output_dir=str(ARTIFACT_DIR / "checkpoints"),
        num_train_epochs=epochs,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        logging_steps=50,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=ds["train"],
        eval_dataset=ds["test"],
        compute_metrics=_compute_metrics,
    )
    trainer.train()

    # Final evaluation with per-class report
    print("\n=== Final Evaluation ===")
    predictions = trainer.predict(ds["test"])
    preds = np.argmax(predictions.predictions, axis=-1)
    labels = predictions.label_ids

    from sklearn.metrics import classification_report
    print(classification_report(labels, preds, target_names=LABEL_NAMES))

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(ARTIFACT_DIR))
    tokenizer.save_pretrained(str(ARTIFACT_DIR))
    print(f"Model saved to {ARTIFACT_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Train Kenyan risk classifier")
    parser.add_argument("--model", default="distilbert-base-multilingual-cased")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--csv", default="", help="Path to supplementary CSV (Kaggle auto-detected)")
    args = parser.parse_args()
    train(args.model, args.epochs, args.csv)


if __name__ == "__main__":
    main()
