"""
embedder.py — Sentence embedding generation for complaint texts.

Uses the multilingual sentence-transformers model to produce dense vectors,
which are then fed to the HDBSCAN clusterer.
"""

from __future__ import annotations

from typing import Any

import numpy as np

MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"

# Lazy-loaded model singleton
_model = None


def _get_model():
    """Load the sentence-transformers model (cached after first call)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
        print(f"🔤 Loaded embedding model: {MODEL_NAME}")
    return _model


def embed_complaints(complaints: list[dict[str, Any]]) -> np.ndarray:
    """
    Generate embeddings for a list of complaint dicts.

    Args:
        complaints: Each dict must have a 'text' field.

    Returns:
        np.ndarray of shape (n_complaints, embedding_dim).
    """
    model = _get_model()
    texts = [c["text"] for c in complaints]
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=64,
        normalize_embeddings=True,
    )
    print(f"📐 Generated {embeddings.shape[0]} embeddings (dim={embeddings.shape[1]})")
    return embeddings


def embed_single(text: str) -> np.ndarray:
    """Embed a single string — useful for query-time similarity search."""
    model = _get_model()
    return model.encode([text], normalize_embeddings=True)[0]
