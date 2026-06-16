"""
lifecycle.py — Campaign lifecycle stage detection.

Assigns each campaign cluster one of the following stages based on its
temporal complaint distribution:

  EMERGING   — first complaints appearing, < 7 days of activity
  ACTIVE     — sustained complaint volume
  DORMANT    — gap of ≥ 7 days with no new complaints (may resurface)
  RESURGENT  — activity resumes after a dormancy period
  DECLINED   — complaint rate drops to near-zero after peak
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

DORMANCY_THRESHOLD_DAYS = 7

STAGES = ("EMERGING", "ACTIVE", "DORMANT", "RESURGENT", "DECLINED")


def tag_lifecycles(
    labels,  # np.ndarray or list[int]
    complaints: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """
    Analyze the temporal distribution of each cluster and assign a lifecycle
    stage.

    Returns:
        {cluster_id: {"stage": str, "date_range": [...], "dormancy_gaps": [...]}}
    """
    # Group dates by cluster
    cluster_dates: dict[int, list[datetime]] = defaultdict(list)

    for complaint, label in zip(complaints, labels):
        if label == -1:
            continue
        try:
            dt = datetime.fromisoformat(complaint["date"])
        except (KeyError, ValueError):
            continue
        cluster_dates[int(label)].append(dt)

    # Analyze each cluster
    results: dict[int, dict[str, Any]] = {}
    for cid, dates in cluster_dates.items():
        dates.sort()
        results[cid] = _classify_lifecycle(cid, dates)

    return results


def _classify_lifecycle(
    cluster_id: int, dates: list[datetime]
) -> dict[str, Any]:
    """Classify a single cluster's lifecycle."""
    if not dates:
        return {"stage": "EMERGING", "date_range": [], "dormancy_gaps": []}

    span = (dates[-1] - dates[0]).days
    gaps = _find_dormancy_gaps(dates)

    # Determine stage
    if gaps and dates[-1] > gaps[-1]["end"]:
        stage = "RESURGENT"
    elif gaps:
        stage = "DORMANT"
    elif span < 7:
        stage = "EMERGING"
    else:
        # Check if complaint rate is declining
        midpoint = dates[0] + timedelta(days=span // 2)
        first_half = sum(1 for d in dates if d < midpoint)
        second_half = len(dates) - first_half
        stage = "DECLINED" if second_half < first_half * 0.3 else "ACTIVE"

    return {
        "cluster_id": cluster_id,
        "stage": stage,
        "date_range": [dates[0].isoformat(), dates[-1].isoformat()],
        "total_complaints": len(dates),
        "span_days": span,
        "dormancy_gaps": [
            {"start": g["start"].isoformat(), "end": g["end"].isoformat(), "days": g["days"]}
            for g in gaps
        ],
    }


def _find_dormancy_gaps(dates: list[datetime]) -> list[dict[str, Any]]:
    """Find gaps ≥ DORMANCY_THRESHOLD_DAYS between consecutive complaints."""
    gaps = []
    for i in range(1, len(dates)):
        delta = (dates[i] - dates[i - 1]).days
        if delta >= DORMANCY_THRESHOLD_DAYS:
            gaps.append(
                {"start": dates[i - 1], "end": dates[i], "days": delta}
            )
    return gaps
