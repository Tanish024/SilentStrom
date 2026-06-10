"""
clusterer.py — HDBSCAN-based complaint clustering.

Groups complaint embeddings into campaign clusters.  Noise points (label -1)
are complaints that don't clearly belong to any campaign.
"""

from __future__ import annotations

from typing import Any

import hdbscan
import numpy as np


def cluster(
    embeddings: np.ndarray,
    min_cluster_size: int = 8,
    min_samples: int = 3,
    metric: str = "euclidean",
) -> np.ndarray:
    """
    Cluster embeddings using HDBSCAN.

    Args:
        embeddings:       (N, D) array of complaint embeddings.
        min_cluster_size:  Minimum members to form a cluster.
        min_samples:       Controls density — higher = more conservative.
        metric:            Distance metric.

    Returns:
        np.ndarray of cluster labels, shape (N,). -1 = noise.
    """
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=metric,
        cluster_selection_method="eom",
        prediction_data=True,
    )
    labels = clusterer.fit_predict(embeddings)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int(np.sum(labels == -1))
    print(f"🔬 HDBSCAN found {n_clusters} clusters, {n_noise} noise points")

    return labels


def get_cluster_summary(
    complaints: list[dict[str, Any]], labels: np.ndarray
) -> list[dict[str, Any]]:
    """
    Build a summary for each cluster: size, date range, top UPI IDs, etc.
    """
    from collections import Counter

    cluster_ids = sorted(set(labels) - {-1})
    summaries = []

    for cid in cluster_ids:
        members = [c for c, lbl in zip(complaints, labels) if lbl == cid]
        all_upis = [u for m in members for u in m.get("upi_ids", m.get("upi_ids_raw", []))]
        dates = sorted([m["date"] for m in members if "date" in m])

        summaries.append(
            {
                "cluster_id": int(cid),
                "size": len(members),
                "date_range": [dates[0], dates[-1]] if dates else [],
                "top_upi_ids": [u for u, _ in Counter(all_upis).most_common(5)],
                "sample_text": members[0]["text"][:200] if members else "",
            }
        )

    return summaries
