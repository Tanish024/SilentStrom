"""
test_clustering.py -- Standalone Phase 3 integration test for SilentStorm.

Pipeline:
    1. Load complaints.json
    2. NER-extract entities for every complaint
    3. Embed all complaint texts
    4. Cluster the embeddings with HDBSCAN
    5. Print diagnostics: cluster label counts, fingerprints, dormancy gap

Run:
    python test_clustering.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).parent / "data" / "complaints.json"

# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════

SEPARATOR = "=" * 72


def _print_header(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def _campaign_prefix(complaint_id: str) -> str:
    """Extract the campaign prefix from a complaint ID, e.g. 'CA' from 'CA-0009'."""
    return complaint_id.split("-")[0][1:]  # 'CA-0009' -> 'A'


# ══════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════

def main() -> None:
    _print_header("SilentStorm -- Phase 3 Clustering Test")

    # ── 1. Load complaints ────────────────────────────────────────────
    print("\n[1/4] Loading complaints ...")
    with open(DATA_PATH, encoding="utf-8") as f:
        complaints: list[dict] = json.load(f)
    print(f"      Loaded {len(complaints)} complaints from {DATA_PATH.name}")

    # Quick breakdown by ground-truth campaign
    gt_counts = Counter(_campaign_prefix(c["id"]) for c in complaints)
    print(f"      Ground-truth campaigns: {dict(sorted(gt_counts.items()))}")

    # ── 2. NER extraction ─────────────────────────────────────────────
    print("\n[2/4] Running NER extraction ...")
    from ner_extractor import extract_entities_batch

    complaints = extract_entities_batch(complaints)
    sample = complaints[0]
    sample_ents = sample.get("entities", {})
    print(f"      Sample entity keys: {list(sample_ents.keys())}")
    print(f"      Sample UPI IDs:     {sample_ents.get('upi_ids', [])[:3]}")

    # ── 3. Embedding ──────────────────────────────────────────────────
    print("\n[3/4] Generating embeddings ...")
    from embedder import embed_complaints

    texts = [c["text"] for c in complaints]
    embeddings = embed_complaints(texts)
    print(f"      Shape: {embeddings.shape}  dtype: {embeddings.dtype}")

    # Sanity: check L2 norms (should be ~= 1.0 if normalised)
    norms = (embeddings ** 2).sum(axis=1) ** 0.5
    print(f"      L2 norm range: [{norms.min():.4f}, {norms.max():.4f}] "
          f"(should be ~= 1.0)")

    # ── 4. Clustering ─────────────────────────────────────────────────
    print("\n[4/4] Clustering with HDBSCAN ...")
    from clusterer import run_clustering, compute_cluster_fingerprint

    labels = run_clustering(embeddings)

    # ── Diagnostics: all-noise check ──────────────────────────────────
    unique_labels = sorted(set(labels))
    if unique_labels == [-1]:
        print("\n[!] ALL complaints fell into noise (cluster -1).")
        print("    Possible causes:")
        print("      * Embeddings may not be L2-normalised")
        print("      * min_cluster_size / min_samples too high")
        print("      * cluster_selection_epsilon too low")
        print("      * The embedding model did not separate the campaigns")
        print("    Check the L2 norm range above -- values far from 1.0 "
              "indicate un-normalised vectors.")
        sys.exit(1)

    # ══════════════════════════════════════════════════════════════════
    # Results
    # ══════════════════════════════════════════════════════════════════

    # ── Cluster label counts ──────────────────────────────────────────
    _print_header("Cluster Label Counts")
    label_counts = Counter(labels)
    for lbl in sorted(label_counts):
        tag = "noise" if lbl == -1 else f"cluster {lbl}"
        print(f"    {tag:>12}  ->  {label_counts[lbl]:>3} complaints")

    n_clusters = len([l for l in unique_labels if l != -1])
    n_noise = label_counts.get(-1, 0)
    print(f"\n    Total clusters: {n_clusters}   |   Noise: {n_noise}")

    # ── Ground-truth vs cluster mapping ───────────────────────────────
    _print_header("Ground-Truth <-> Cluster Mapping")
    # For each cluster, show which ground-truth campaigns are present
    cluster_to_gt: dict[int, Counter] = defaultdict(Counter)
    for c, lbl in zip(complaints, labels):
        camp = _campaign_prefix(c["id"])
        cluster_to_gt[lbl][camp] += 1

    for lbl in sorted(cluster_to_gt):
        tag = "noise" if lbl == -1 else f"cluster {lbl}"
        breakdown = ", ".join(
            f"{camp}={cnt}" for camp, cnt in sorted(cluster_to_gt[lbl].items())
        )
        print(f"    {tag:>12}  ->  {breakdown}")

    # ── Cluster fingerprints ──────────────────────────────────────────
    _print_header("Cluster Fingerprints")
    cluster_ids = sorted(l for l in unique_labels if l != -1)
    for cid in cluster_ids:
        fp = compute_cluster_fingerprint(complaints, labels, cid)
        print(f"\n  -- Cluster {cid} --")
        print(f"    Complaints : {fp['complaint_count']}")
        print(f"    Date range : {fp['date_range']}")
        print(f"    Top UPIs   : {fp['top_upi_ids']}")
        print(f"    Top phones : {fp['top_phones']}")
        print(f"    Top apps   : {fp['top_app_names']}")

    # ── Campaign C dormancy gap analysis ──────────────────────────────
    _print_header("Campaign C -- Dormancy Gap Analysis")

    # Find the cluster that contains the most CC complaints
    cc_cluster = None
    cc_max = 0
    for lbl in cluster_ids:
        cc_count = cluster_to_gt[lbl].get("C", 0)
        if cc_count > cc_max:
            cc_max = cc_count
            cc_cluster = lbl

    if cc_cluster is None:
        print("    [!] No cluster found with Campaign C complaints.")
    else:
        print(f"    Campaign C mapped primarily to cluster {cc_cluster} "
              f"({cc_max} complaints)")

        # Gather dates for CC complaints in that cluster
        cc_dates = []
        for c, lbl in zip(complaints, labels):
            if lbl == cc_cluster and _campaign_prefix(c["id"]) == "C":
                try:
                    cc_dates.append(datetime.fromisoformat(c["date"]))
                except (KeyError, ValueError):
                    pass

        cc_dates.sort()

        if len(cc_dates) < 2:
            print("    [!] Not enough dated complaints to analyse gaps.")
        else:
            print(f"    Date range: {cc_dates[0].date()} -> {cc_dates[-1].date()}")
            print(f"    Total dated complaints: {len(cc_dates)}")

            # Find gaps ≥ 7 days
            DORMANCY_DAYS = 7
            gaps = []
            for i in range(1, len(cc_dates)):
                delta = (cc_dates[i] - cc_dates[i - 1]).days
                if delta >= DORMANCY_DAYS:
                    gaps.append({
                        "from": cc_dates[i - 1].date(),
                        "to": cc_dates[i].date(),
                        "days": delta,
                    })

            if gaps:
                print(f"    [PASS] Found {len(gaps)} dormancy gap(s) (>= {DORMANCY_DAYS} days):")
                for g in gaps:
                    print(f"       {g['from']} -> {g['to']}  ({g['days']} days)")
            else:
                print(f"    [FAIL] No dormancy gaps >= {DORMANCY_DAYS} days found.")

    # ── Final summary ─────────────────────────────────────────────────
    _print_header("Summary")
    status = "[PASS]" if n_clusters == 4 else f"[!] Expected 4 clusters, got {n_clusters}"
    print(f"    Clusters found: {n_clusters}   {status}")
    print(f"    Noise points:   {n_noise}")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
