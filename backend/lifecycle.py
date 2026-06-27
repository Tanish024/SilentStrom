"""
lifecycle.py — Campaign lifecycle stage detection & mutation alerting.

Assigns each campaign cluster one of the following stages based on its
temporal complaint distribution:

  birth     — first complaints appearing, < 3 days of activity
  scaling   — complaint rate is increasing rapidly
  detected  — high sustained volume (likely detected by authorities)
  dormant   — gap of >= 7 days with no new complaints
  active    — sustained complaint volume (steady state)
  unknown   — insufficient data to classify

Also provides:
  check_for_mutations()  — cosine similarity of a dormant campaign centroid
                           vs recent complaint embeddings to detect relaunches
  generate_alert()       — structured alert dict for probable campaign relaunch
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

DORMANCY_THRESHOLD_DAYS = 7


# ══════════════════════════════════════════════════════════════════════
# 1. Campaign timeline
# ══════════════════════════════════════════════════════════════════════

def compute_campaign_timeline(
    complaints: list[dict[str, Any]],
    cluster_id: int,
) -> list[dict[str, Any]]:
    """
    Compute daily complaint count for a specific cluster.

    Args:
        complaints: List of complaint dicts, each with "date" and "cluster"
                    (or use the original list + separate labels).
        cluster_id: The cluster to analyze.

    Returns:
        Sorted list of {"date": "YYYY-MM-DD", "count": int} dicts,
        one entry per day that had at least one complaint.
    """
    daily: Counter = Counter()

    for c in complaints:
        # Support both 'cluster' key and 'label' key
        label = c.get("cluster", c.get("label", -1))
        if int(label) != cluster_id:
            continue

        date_str = c.get("date", "")
        if not date_str:
            continue

        # Normalise to YYYY-MM-DD (strip time if present)
        try:
            dt = datetime.fromisoformat(date_str)
            day = dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            day = date_str[:10]  # raw truncation fallback

        daily[day] += 1

    # Sort by date
    timeline = [
        {"date": day, "count": count}
        for day, count in sorted(daily.items())
    ]

    return timeline


# ══════════════════════════════════════════════════════════════════════
# 2. Lifecycle stage detection
# ══════════════════════════════════════════════════════════════════════

def detect_lifecycle_stage(timeline: list[dict[str, Any]]) -> str:
    """
    Determine the lifecycle stage of a campaign based on its daily
    complaint timeline.

    Decision logic (based on the last 3 days of activity):
      - If timeline has < 2 entries → 'unknown'
      - If total span < 3 days → 'birth'
      - If activity gap >= DORMANCY_THRESHOLD_DAYS at end → 'dormant'
      - If the last 3 data points show increasing counts → 'scaling'
      - If average daily count in last 3 entries >= 3 → 'detected'
      - Otherwise → 'active'

    Args:
        timeline: Sorted list of {"date": str, "count": int} from
                  compute_campaign_timeline().

    Returns:
        One of: 'birth', 'scaling', 'detected', 'dormant', 'active', 'unknown'
    """
    if not timeline or len(timeline) < 2:
        return "unknown"

    # Parse dates
    dates = []
    for entry in timeline:
        try:
            dates.append(datetime.fromisoformat(entry["date"]))
        except (ValueError, TypeError):
            continue

    if len(dates) < 2:
        return "unknown"

    dates.sort()
    total_span = (dates[-1] - dates[0]).days

    # ── Birth: very early stage ───────────────────────────────────────
    if total_span < 3:
        return "birth"

    # ── Dormant: large gap at the end ─────────────────────────────────
    # Check if the gap between the last two entries is >= threshold
    if len(dates) >= 2:
        last_gap = (dates[-1] - dates[-2]).days
        if last_gap >= DORMANCY_THRESHOLD_DAYS:
            return "dormant"

    # Also check: if the campaign has any internal dormancy gaps
    for i in range(1, len(dates)):
        gap = (dates[i] - dates[i - 1]).days
        if gap >= DORMANCY_THRESHOLD_DAYS:
            # If the gap is not at the end (i.e., there's activity after),
            # the campaign is still active; but if gap is internal, mark dormant
            # only if the remaining activity after the gap is minimal
            remaining_after_gap = len(dates) - i
            if remaining_after_gap <= 2:
                return "dormant"

    # ── Last 3 entries analysis ───────────────────────────────────────
    last_3 = timeline[-3:] if len(timeline) >= 3 else timeline
    counts = [e["count"] for e in last_3]

    # Scaling: counts are strictly increasing
    if len(counts) >= 3 and counts[-1] > counts[-2] > counts[-3]:
        return "scaling"

    # Detected: high volume (avg >= 3 complaints/day in recent window)
    avg_recent = sum(counts) / len(counts)
    if avg_recent >= 3:
        return "detected"

    # ── Default: active ───────────────────────────────────────────────
    return "active"


# ══════════════════════════════════════════════════════════════════════
# 3. Mutation / relaunch detection
# ══════════════════════════════════════════════════════════════════════

def check_for_mutations(
    dormant_cluster_embedding: np.ndarray,
    all_recent_embeddings: np.ndarray,
) -> list[float]:
    """
    Compare a dormant campaign's centroid embedding against each new
    complaint embedding to detect potential campaign relaunches.

    Uses cosine similarity: a high score (>0.75) suggests the new
    complaint is thematically similar to the dormant campaign.

    Args:
        dormant_cluster_embedding: 1-D array (768,) — the centroid of the
            dormant campaign cluster (mean of its member embeddings).
        all_recent_embeddings: 2-D array (N, 768) — embeddings of recent
            complaints not yet assigned to a cluster.

    Returns:
        List of N floats — cosine similarity scores in [-1, 1].
    """
    # Ensure inputs are numpy arrays
    centroid = np.asarray(dormant_cluster_embedding, dtype=np.float32)
    recent = np.asarray(all_recent_embeddings, dtype=np.float32)

    # Handle 1-D case (single recent embedding)
    if recent.ndim == 1:
        recent = recent.reshape(1, -1)

    # L2 normalise for cosine similarity
    centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-10)
    norms = np.linalg.norm(recent, axis=1, keepdims=True) + 1e-10
    recent_norm = recent / norms

    # Dot product = cosine similarity (after normalisation)
    similarities = recent_norm @ centroid_norm

    return similarities.tolist()


# ══════════════════════════════════════════════════════════════════════
# 4. Alert generation
# ══════════════════════════════════════════════════════════════════════

def generate_alert(
    campaign_fingerprint: dict[str, Any],
    similarity_score: float,
) -> dict[str, Any]:
    """
    Generate a structured relaunch alert.

    Args:
        campaign_fingerprint: Output of clusterer.compute_cluster_fingerprint(),
            expected to contain 'cluster_id', 'top_upi_ids', 'top_app_names'.
        similarity_score: Cosine similarity (0–1) between dormant campaign
            centroid and the suspicious new complaint.

    Returns:
        {
            "alert_type": "PROBABLE_RELAUNCH",
            "campaign_id": <cluster_id>,
            "similarity": "<rounded %>",
            "known_upis": [...],
            "known_apps": [...],
            "action": "Flag for investigation — dormant campaign may be relaunching with similar tactics.",
            "timestamp": "<ISO 8601>"
        }
    """
    return {
        "alert_type": "PROBABLE_RELAUNCH",
        "campaign_id": campaign_fingerprint.get("cluster_id", "unknown"),
        "similarity": f"{round(similarity_score * 100)}%",
        "known_upis": campaign_fingerprint.get("top_upi_ids", []),
        "known_apps": campaign_fingerprint.get("top_app_names", []),
        "action": (
            "Flag for investigation — dormant campaign may be relaunching "
            "with similar tactics."
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════════════
# 5. Bulk lifecycle tagging (used by ingest pipeline)
# ══════════════════════════════════════════════════════════════════════

def tag_lifecycles(
    labels,  # np.ndarray or list[int]
    complaints: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """
    Analyze the temporal distribution of each cluster and assign a
    lifecycle stage using the new detect_lifecycle_stage() logic.

    Returns:
        {cluster_id: {"stage": str, "timeline": [...], ...}}
    """
    # Attach cluster labels to complaints
    enriched = []
    for c, label in zip(complaints, labels):
        enriched.append({**c, "cluster": int(label)})

    # Get unique cluster IDs (skip noise = -1)
    cluster_ids = sorted(set(int(l) for l in labels if int(l) != -1))

    results: dict[int, dict[str, Any]] = {}
    for cid in cluster_ids:
        timeline = compute_campaign_timeline(enriched, cid)
        stage = detect_lifecycle_stage(timeline)

        # Date range from timeline
        dates = [e["date"] for e in timeline]
        date_range = [dates[0], dates[-1]] if dates else []

        # Total complaints
        total = sum(e["count"] for e in timeline)

        # Dormancy gaps
        gaps = []
        for i in range(1, len(dates)):
            try:
                d1 = datetime.fromisoformat(dates[i - 1])
                d2 = datetime.fromisoformat(dates[i])
                delta = (d2 - d1).days
                if delta >= DORMANCY_THRESHOLD_DAYS:
                    gaps.append({
                        "start": dates[i - 1],
                        "end": dates[i],
                        "days": delta,
                    })
            except (ValueError, TypeError):
                continue

        results[cid] = {
            "cluster_id": cid,
            "stage": stage,
            "date_range": date_range,
            "total_complaints": total,
            "timeline": timeline,
            "dormancy_gaps": gaps,
        }

    return results
