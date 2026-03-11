"""
Upload the trained Kenyan classifier to HuggingFace Hub.

Usage:
  python scripts/upload_model_to_hub.py --repo-id johnombuya/mwavuli-kenyan-classifier

Requires HF_TOKEN in .env (a HuggingFace access token with write permission).
Get one at: https://huggingface.co/settings/tokens
"""

import argparse
import os
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv
load_dotenv(_backend_root / ".env")

DEFAULT_MODEL_DIR = _backend_root / "models" / "artifacts" / "kenyan_classifier"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload Kenyan classifier model to HuggingFace Hub"
    )
    parser.add_argument(
        "--repo-id",
        required=True,
        help="HuggingFace repo ID (e.g. johnombuya/mwavuli-kenyan-classifier)",
    )
    parser.add_argument(
        "--model-dir",
        default=str(DEFAULT_MODEL_DIR),
        help=f"Path to model artifact folder (default: {DEFAULT_MODEL_DIR})",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        default=True,
        help="Create the repo as private (default: true)",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Create the repo as public instead of private",
    )
    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        print(f"Model directory not found: {model_dir}")
        print("Train the model first or specify the correct --model-dir.")
        return 1

    expected_files = ["config.json"]
    missing = [f for f in expected_files if not (model_dir / f).exists()]
    if missing:
        print(f"Model directory is missing required files: {missing}")
        return 1

    token = os.getenv("HF_TOKEN", "")
    if not token:
        print("HF_TOKEN not set in .env — get one at https://huggingface.co/settings/tokens")
        return 1

    private = not args.public

    from huggingface_hub import HfApi, create_repo

    api = HfApi(token=token)

    print(f"Creating repo {args.repo_id} (private={private})...")
    try:
        create_repo(
            repo_id=args.repo_id,
            token=token,
            repo_type="model",
            private=private,
            exist_ok=True,
        )
    except Exception as e:
        print(f"Warning: Could not create repo (may already exist): {e}")

    print(f"Uploading {model_dir} to {args.repo_id}...")
    api.upload_folder(
        folder_path=str(model_dir),
        repo_id=args.repo_id,
        repo_type="model",
        commit_message="Upload Mwavuli Kenyan risk classifier",
    )

    print(f"Done! Model available at: https://huggingface.co/{args.repo_id}")
    print(f"\nTo use it, add to your .env:")
    print(f"  HF_MODEL_REPO={args.repo_id}")
    print(f"  HF_TOKEN={token[:8]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
