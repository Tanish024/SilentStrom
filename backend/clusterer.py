"""
clusterer.py — HDBSCAN-based complaint clustering for SilentStorm.

Groups complaint embeddings into campaign clusters.  Noise points (label -1)
are complaints that don't clearly belong to any campaign.

Usage:
    from clusterer import run_clustering, compute_cluster_fingerprint
    labels = run_clustering(embeddings)
    fp     = compute_cluster_fingerprint(complaints, labels, cluster_id=0)
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import hdbscan
import numpy as np


# ══════════════════════════════════════════════════════════════════════
# 1. Clustering
# ══════════════════════════════════════════════════════════════════════

def run_clustering(
    embeddings: np.ndarray,
    min_cluster_size: int = 5,
    min_samples: int = 2,
    metric: str = "euclidean",
    cluster_selection_epsilon: float = 0.3,
) -> list[int]:
    """
    Cluster complaint embeddings using HDBSCAN.

    Args:
        embeddings:                (N, D) array of complaint embeddings.
        min_cluster_size:          Minimum members to form a cluster.
        min_samples:               Controls density — higher = more conservative.
        metric:                    Distance metric.
        cluster_selection_epsilon:  Merge clusters closer than this threshold,
                                    helping consolidate near-duplicate campaigns.

    Returns:
        List of integer cluster labels, length N.  -1 = noise.
    """
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=metric,
        cluster_selection_epsilon=cluster_selection_epsilon,
        cluster_selection_method="eom",
        prediction_data=True,
    )
    labels: np.ndarray = clusterer.fit_predict(embeddings)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int(np.sum(labels == -1))
    print(f"[clusterer] HDBSCAN: {n_clusters} clusters, {n_noise} noise points "
          f"(out of {len(labels)} complaints)")

    return labels.tolist()


# ══════════════════════════════════════════════════════════════════════
# 2. Cluster fingerprinting
# ══════════════════════════════════════════════════════════════════════

def compute_cluster_fingerprint(
    complaints: list[dict[str, Any]],
    labels: list[int],
    cluster_id: int,
) -> dict[str, Any]:
    """
    Build a concise fingerprint for a single cluster.

    Gathers all complaints assigned to *cluster_id*, then extracts the
    most-common UPI IDs, phone numbers, and app names across the cluster
    as well as the date range.

    Args:
        complaints:  List of complaint dicts (after NER enrichment).
        labels:      Parallel list of cluster labels from run_clustering().
        cluster_id:  The cluster to fingerprint.

    Returns:
        {
            "cluster_id":      int,
            "complaint_count": int,
            "top_upi_ids":     list[str]   (up to 5 unique),
            "top_phones":      list[str]   (up to 5 unique),
            "top_app_names":   list[str]   (up to 3 unique),
            "date_range":      [min_date, max_date] or []
        }
    """
    # ── Gather members ────────────────────────────────────────────────
    members = [
        c for c, lbl in zip(complaints, labels) if lbl == cluster_id
    ]

    if not members:
        return {
            "cluster_id": cluster_id,
            "complaint_count": 0,
            "top_upi_ids": [],
            "top_phones": [],
            "top_app_names": [],
            "date_range": [],
        }

    # ── Collect entities from both NER-enriched and raw fields ────────
    all_upis: list[str] = []
    all_phones: list[str] = []
    all_apps: list[str] = []
    all_dates: list[str] = []

    for m in members:
        # UPI IDs — prefer NER-extracted, fall back to raw
        ents = m.get("entities", {})
        all_upis.extend(ents.get("upi_ids", []))
        all_upis.extend(m.get("upi_ids_raw", []))

        # Phones — prefer NER-extracted, fall back to raw
        all_phones.extend(ents.get("phones", []))
        all_phones.extend(m.get("phone_raw", []))

        # App names — NER-extracted only
        all_apps.extend(ents.get("app_names", []))

        # Dates
        if "date" in m and m["date"]:
            all_dates.append(m["date"])

    # ── Top-N by frequency ────────────────────────────────────────────
    top_upi_ids = [u for u, _ in Counter(all_upis).most_common(5)]
    top_phones = [p for p, _ in Counter(all_phones).most_common(5)]
    top_app_names = [a for a, _ in Counter(all_apps).most_common(3)]

    # ── Date range ────────────────────────────────────────────────────
    all_dates.sort()
    date_range = [all_dates[0], all_dates[-1]] if all_dates else []

    return {
        "cluster_id": cluster_id,
        "complaint_count": len(members),
        "top_upi_ids": top_upi_ids,
        "top_phones": top_phones,
        "top_app_names": top_app_names,
        "date_range": date_range,
    }
