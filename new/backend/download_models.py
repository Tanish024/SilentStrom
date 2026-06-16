"""
download_models.py — One-time script to pre-download and cache the
sentence-transformers model used by the SilentStorm embedder.

Run once before starting the pipeline:
    python download_models.py
"""

import sys
import time

MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"


def main() -> None:
    print(f"⏳ Downloading model: {MODEL_NAME} ...")
    start = time.time()

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)
    except Exception as exc:
        print(f"❌ Download failed: {exc}", file=sys.stderr)
        sys.exit(1)

    elapsed = time.time() - start

    # Quick sanity check — encode a throwaway sentence
    _ = model.encode(["SilentStorm model cache verification"])

    cache_dir = model[0].auto_model.config._name_or_path
    print(f"✅ Model '{MODEL_NAME}' cached successfully.")
    print(f"   Cache location : {cache_dir}")
    print(f"   Download time  : {elapsed:.1f}s")
    print(f"   Embedding dim  : {model.get_sentence_embedding_dimension()}")


if __name__ == "__main__":
    main()
