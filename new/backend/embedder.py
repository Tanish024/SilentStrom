"""
embedder.py — Sentence embedding generation for SilentStorm complaint texts.

Singleton pattern:  the model is loaded once via get_model() and reused.
Produces 768-dimensional L2-normalised float32 vectors using
'paraphrase-multilingual-mpnet-base-v2' (supports Hindi, English, and mixed).

Usage:
    from embedder import embed_complaints, cosine_similarity
    vecs = embed_complaints(["complaint one", "complaint two"])   # (2, 768)
    sim  = cosine_similarity(vecs[0], vecs[1])                    # float

Run this file directly to execute the built-in test block:
    python embedder.py
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"

# ══════════════════════════════════════════════════════════════════════
# 1. Singleton model loader
# ══════════════════════════════════════════════════════════════════════

_model = None


def get_model():
    """
    Return the SentenceTransformer model, loading it on first call.
    Subsequent calls return the cached instance (singleton).
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        print(f"[embedder] Loading model '{MODEL_NAME}' ...")
        _model = SentenceTransformer(MODEL_NAME)
        dim = _model.get_sentence_embedding_dimension()
        print(f"[embedder] Model ready — embedding dimension = {dim}")
    return _model


# ══════════════════════════════════════════════════════════════════════
# 2. Embedding functions
# ══════════════════════════════════════════════════════════════════════

def embed_complaints(texts: list[str]) -> np.ndarray:
    """
    Embed a list of complaint texts.

    Args:
        texts: Raw complaint strings (any language).

    Returns:
        np.ndarray of shape (N, 768), dtype float32, L2-normalised.
    """
    model = get_model()
    embeddings: np.ndarray = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=len(texts) > 50,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    embeddings = embeddings.astype(np.float32)
    assert embeddings.shape == (len(texts), 768), (
        f"Expected shape ({len(texts)}, 768), got {embeddings.shape}"
    )
    return embeddings


def embed_single(text: str) -> np.ndarray:
    """Embed a single string and return a 1-D vector of shape (768,)."""
    return embed_complaints([text])[0]


# ══════════════════════════════════════════════════════════════════════
# 3. Cosine similarity
# ══════════════════════════════════════════════════════════════════════

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity between two vectors.

    Because embed_complaints() already L2-normalises, this reduces to
    a simple dot product.  We still guard against un-normalised inputs.
    """
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b) + 1e-10)
    return float(np.dot(a_norm, b_norm))


# ══════════════════════════════════════════════════════════════════════
# 4. Built-in test block
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    from pathlib import Path

    DATA_PATH = Path(__file__).parent / "data" / "complaints.json"

    print("=" * 72)
    print("  SilentStorm Embedder — Test Results")
    print("=" * 72)

    # ── Load complaints ───────────────────────────────────────────────
    with open(DATA_PATH, encoding="utf-8") as f:
        all_complaints = json.load(f)

    print(f"\nLoaded {len(all_complaints)} complaints from {DATA_PATH.name}")

    # ── Pick 5 complaints: 2 from Campaign A (one Hindi, one English),
    #    2 from Campaign B (one Hindi, one English), 1 from Campaign D
    #    so we can test within-campaign vs cross-campaign similarity. ──

    def find_by_campaign_and_lang(camp_prefix: str, lang: str):
        """Find the first complaint matching campaign prefix and language."""
        for c in all_complaints:
            if c["id"].startswith(camp_prefix) and c.get("language") == lang:
                return c
        # Fallback: just match campaign
        for c in all_complaints:
            if c["id"].startswith(camp_prefix):
                return c
        return None

    ca_hi = find_by_campaign_and_lang("CA", "hi")
    ca_en = find_by_campaign_and_lang("CA", "en")
    cb_hi = find_by_campaign_and_lang("CB", "hi")
    cb_en = find_by_campaign_and_lang("CB", "en")
    cd_any = find_by_campaign_and_lang("CD", "en") or find_by_campaign_and_lang("CD", "hi")

    selected = [ca_hi, ca_en, cb_hi, cb_en, cd_any]
    labels = ["CA-Hindi", "CA-English", "CB-Hindi", "CB-English", "CD"]

    # Check we found all 5
    for s, lbl in zip(selected, labels):
        if s is None:
            print(f"WARNING: Could not find complaint for {lbl}", file=sys.stderr)
    selected = [s for s in selected if s is not None]
    labels = labels[: len(selected)]

    texts = [s["text"] for s in selected]

    print(f"\nEmbedding {len(texts)} selected complaints ...")
    vecs = embed_complaints(texts)
    print(f"  Shape: {vecs.shape}  dtype: {vecs.dtype}")

    # ── Print pairwise cosine similarities ────────────────────────────
    print(f"\n{'Pairwise Cosine Similarity':^60}")
    print("-" * 60)

    # Header row
    header = f"{'':>14}" + "".join(f"{lbl:>12}" for lbl in labels)
    print(header)

    for i, lbl_i in enumerate(labels):
        row = f"{lbl_i:>14}"
        for j, lbl_j in enumerate(labels):
            sim = cosine_similarity(vecs[i], vecs[j])
            row += f"{sim:>12.4f}"
        print(row)

    # ── Verify within-campaign similarity > 0.6 ──────────────────────
    print(f"\n{'Verification':^60}")
    print("-" * 60)

    pairs_to_check = [
        (0, 1, "CA-Hindi vs CA-English"),
        (2, 3, "CB-Hindi vs CB-English"),
    ]

    all_passed = True
    for i, j, desc in pairs_to_check:
        if i < len(vecs) and j < len(vecs):
            sim = cosine_similarity(vecs[i], vecs[j])
            passed = sim > 0.6
            status = "PASS" if passed else "FAIL"
            print(f"  {desc:>30}  sim={sim:.4f}  [{status}]")
            if not passed:
                all_passed = False

    # Cross-campaign should be lower
    cross_pairs = [
        (0, 2, "CA-Hindi vs CB-Hindi (cross-campaign)"),
        (1, 4, "CA-English vs CD (cross-campaign)"),
    ]

    for i, j, desc in cross_pairs:
        if i < len(vecs) and j < len(vecs):
            sim = cosine_similarity(vecs[i], vecs[j])
            print(f"  {desc:>30}  sim={sim:.4f}  [info]")

    print("\n" + "=" * 72)
    if all_passed:
        print("  All within-campaign similarity checks PASSED (> 0.6)")
    else:
        print("  Some checks FAILED — see above")
    print("=" * 72)
