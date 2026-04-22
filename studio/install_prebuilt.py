"""
Duino API — studio/install_prebuilt.py
Downloads a pre-quantized model from HuggingFace Hub for fast startup.
For platforms where compiling bitsandbytes is not possible (e.g. Windows CPU).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

PREBUILT_MODELS = {
    "gemma-4-2b-bnb-4bit":  "unsloth/gemma-2-2b-it-bnb-4bit",   # fallback until Gemma 4 available
    "gemma-4-9b-bnb-4bit":  "unsloth/gemma-2-9b-it-bnb-4bit",
    "gemma-4-2b-awq":       "google/gemma-2-2b-it",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download pre-built model weights")
    parser.add_argument(
        "model",
        choices=list(PREBUILT_MODELS.keys()),
        help="Model variant to download",
    )
    parser.add_argument(
        "--hf-token",
        default=os.environ.get("HF_TOKEN"),
        help="HuggingFace API token",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(Path.home() / ".cache" / "duino_api" / "models"),
        help="Directory to cache model weights",
    )
    args = parser.parse_args()

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("[ERROR] huggingface-hub not installed. Run: pip install huggingface-hub")
        sys.exit(1)

    hf_name = PREBUILT_MODELS[args.model]
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading: {hf_name}")
    print(f"Cache dir  : {cache_dir}")

    local_dir = snapshot_download(
        repo_id=hf_name,
        local_dir=str(cache_dir / args.model),
        token=args.hf_token,
        ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
    )

    print(f"\n✅ Model downloaded to: {local_dir}")
    print(f"   To use: set DEFAULT_MODEL path to {local_dir}")


if __name__ == "__main__":
    main()
