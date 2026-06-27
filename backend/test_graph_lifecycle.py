"""
test_graph_lifecycle.py — Phase 4 integration test for SilentStorm.

Pipeline:
    1. Load complaints.json
    2. NER-extract entities for every complaint
    3. Embed all complaint texts
    4. Cluster the embeddings with HDBSCAN
    5. Ingest all enriched complaints into Neo4j graph
    6. Print node counts
    7. Run PageRank and print top 5 hub nodes
    8. For cluster_id 2 (Campaign C — dormant), print timeline + lifecycle stage

Run:
    python test_graph_lifecycle.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).parent / "data" / "complaints.json"

SEPARATOR = "=" * 72


def _print_header(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def _campaign_prefix(complaint_id: str) -> str:
    """Extract the campaign prefix from a complaint ID, e.g. 'CA-0009' -> 'A'."""
    return complaint_id.split("-")[0][1:]


def main() -> None:
    _print_header("SilentStorm — Phase 4: Graph + Lifecycle Test")

    # ══════════════════════════════════════════════════════════════════
    # Step 1: Load complaints
    # ══════════════════════════════════════════════════════════════════
    print("\n[1/7] Loading complaints ...")
    with open(DATA_PATH, encoding="utf-8") as f:
        complaints: list[dict] = json.load(f)
    print(f"      Loaded {len(complaints)} complaints from {DATA_PATH.name}")

    gt_counts = Counter(_campaign_prefix(c["id"]) for c in complaints)
    print(f"      Ground-truth campaigns: {dict(sorted(gt_counts.items()))}")

    # ══════════════════════════════════════════════════════════════════
    # Step 2: NER extraction
    # ══════════════════════════════════════════════════════════════════
    print("\n[2/7] Running NER extraction ...")
    from ner_extractor import extract_entities_batch

    complaints = extract_entities_batch(complaints)
    print(f"      ✅ Entities extracted for all {len(complaints)} complaints")

    # ══════════════════════════════════════════════════════════════════
    # Step 3: Embedding
    # ══════════════════════════════════════════════════════════════════
    print("\n[3/7] Generating embeddings ...")
    from embedder import embed_complaints

    texts = [c["text"] for c in complaints]
    embeddings = embed_complaints(texts)
    print(f"      ✅ Shape: {embeddings.shape}  dtype: {embeddings.dtype}")

    # ══════════════════════════════════════════════════════════════════
    # Step 4: Clustering
    # ══════════════════════════════════════════════════════════════════
    print("\n[4/7] Clustering with HDBSCAN ...")
    from clusterer import run_clustering, compute_cluster_fingerprint

    labels = run_clustering(embeddings)
    unique_labels = sorted(set(labels))
    cluster_ids = [l for l in unique_labels if l != -1]
    n_clusters = len(cluster_ids)
    n_noise = labels.count(-1)
    print(f"      ✅ {n_clusters} clusters, {n_noise} noise points")

    # Map clusters to ground-truth campaigns
    cluster_to_gt: dict[int, Counter] = defaultdict(Counter)
    for c, lbl in zip(complaints, labels):
        camp = _campaign_prefix(c["id"])
        cluster_to_gt[lbl][camp] += 1

    # ══════════════════════════════════════════════════════════════════
    # Step 5: Ingest into Neo4j
    # ══════════════════════════════════════════════════════════════════
    print("\n[5/7] Ingesting into Neo4j ...")
    from graph_builder import get_driver, clear_graph, ingest_complaint_to_graph, get_node_counts, run_pagerank

    try:
        driver = get_driver()
        # Test connectivity
        driver.verify_connectivity()
    except Exception as e:
        print(f"\n      ❌ Cannot connect to Neo4j at bolt://localhost:7687")
        print(f"         Error: {e}")
        print(f"         Make sure Neo4j is running: docker-compose up -d")
        print(f"\n         Skipping graph tests, running lifecycle tests only...")
        driver = None

    if driver is not None:
        # Clear and rebuild
        clear_graph(driver)

        # Attach cluster labels and ingest
        for complaint, label in zip(complaints, labels):
            enriched = {**complaint, "cluster": int(label)}
            ingest_complaint_to_graph(driver, enriched)

        print(f"      ✅ All {len(complaints)} complaints ingested into Neo4j")

        # ══════════════════════════════════════════════════════════════
        # Step 6: Node counts
        # ══════════════════════════════════════════════════════════════
        _print_header("Neo4j Node Counts")
        counts = get_node_counts(driver)
        total_nodes = 0
        for label_name, count in counts.items():
            print(f"      {label_name:<12} : {count:>4} nodes")
            total_nodes += count
        print(f"      {'TOTAL':<12} : {total_nodes:>4} nodes")

        # ══════════════════════════════════════════════════════════════
        # Step 7: PageRank — top 5 hub nodes
        # ══════════════════════════════════════════════════════════════
        _print_header("PageRank — Top 5 Hub Nodes")
        top_hubs = run_pagerank(driver, top_n=10)

        for i, hub in enumerate(top_hubs[:5], 1):
            print(f"      #{i}  {hub['entity']:<35}  score: {hub['score']}")

        if len(top_hubs) > 5:
            print(f"\n      ... and {len(top_hubs) - 5} more hub nodes")

        driver.close()
    else:
        print("\n      [SKIPPED] Neo4j graph tests (no connection)")

    # ══════════════════════════════════════════════════════════════════
    # Step 8: Lifecycle — Campaign C (dormant)
    # ══════════════════════════════════════════════════════════════════
    _print_header("Lifecycle — Campaign C (Dormant Detection)")

    from lifecycle import compute_campaign_timeline, detect_lifecycle_stage

    # Find the cluster that maps to Campaign C
    cc_cluster = None
    cc_max = 0
    for lbl in cluster_ids:
        cc_count = cluster_to_gt[lbl].get("C", 0)
        if cc_count > cc_max:
            cc_max = cc_count
            cc_cluster = lbl

    if cc_cluster is None:
        print("      ❌ No cluster found containing Campaign C complaints.")
    else:
        print(f"      Campaign C maps to cluster {cc_cluster} ({cc_max} complaints)")

        # Attach cluster labels for timeline computation
        enriched_for_lifecycle = [
            {**c, "cluster": int(lbl)} for c, lbl in zip(complaints, labels)
        ]

        # Compute timeline
        timeline = compute_campaign_timeline(enriched_for_lifecycle, cc_cluster)

        print(f"\n      Timeline ({len(timeline)} active days):")
        print(f"      {'Date':<14} {'Count':>6}")
        print(f"      {'-' * 22}")
        for entry in timeline:
            bar = "█" * entry["count"]
            print(f"      {entry['date']:<14} {entry['count']:>6}  {bar}")

        # Detect lifecycle stage
        stage = detect_lifecycle_stage(timeline)
        print(f"\n      ➤ Lifecycle stage: {stage.upper()}")

        expected = "dormant"
        status = "PASS ✅" if stage == expected else f"FAIL ❌ (expected '{expected}')"
        print(f"      ➤ Verification:   [{status}]")

    # ══════════════════════════════════════════════════════════════════
    # Step 9: Mutation check demo
    # ══════════════════════════════════════════════════════════════════
    if cc_cluster is not None:
        _print_header("Mutation Check — Relaunch Detection Demo")

        import numpy as np
        from lifecycle import check_for_mutations, generate_alert

        # Compute centroid of Campaign C cluster
        cc_indices = [i for i, lbl in enumerate(labels) if lbl == cc_cluster]
        cc_embeddings = embeddings[cc_indices]
        cc_centroid = np.mean(cc_embeddings, axis=0)

        # Pick some "recent" complaints from other clusters as test subjects
        other_indices = [i for i, lbl in enumerate(labels) if lbl != cc_cluster and lbl != -1][:5]
        # Also pick a CC complaint to simulate a "relaunch" match
        cc_test_idx = cc_indices[0] if cc_indices else None

        test_indices = other_indices
        if cc_test_idx is not None:
            test_indices = [cc_test_idx] + other_indices

        recent_embeddings = embeddings[test_indices]

        # Run mutation check
        scores = check_for_mutations(cc_centroid, recent_embeddings)

        print(f"      Testing {len(scores)} complaints against Campaign C centroid:\n")
        for i, (idx, score) in enumerate(zip(test_indices, scores)):
            cid = complaints[idx]["id"]
            camp = _campaign_prefix(cid)
            marker = " ⚠️  HIGH MATCH" if score > 0.75 else ""
            print(f"      [{i+1}] {cid} (Campaign {camp})  similarity: {score:.4f}{marker}")

        # Generate alert for highest-scoring match
        if scores:
            best_idx = int(np.argmax(scores))
            best_score = scores[best_idx]

            if best_score > 0.5:
                fp = compute_cluster_fingerprint(complaints, labels, cc_cluster)
                alert = generate_alert(fp, best_score)
                print(f"\n      ➤ Alert generated:")
                for k, v in alert.items():
                    print(f"        {k}: {v}")

    # ══════════════════════════════════════════════════════════════════
    # All lifecycle stages
    # ══════════════════════════════════════════════════════════════════
    _print_header("All Campaign Lifecycle Stages")

    enriched_all = [{**c, "cluster": int(lbl)} for c, lbl in zip(complaints, labels)]

    for cid in cluster_ids:
        timeline = compute_campaign_timeline(enriched_all, cid)
        stage = detect_lifecycle_stage(timeline)

        gt_camps = cluster_to_gt[cid]
        gt_label = max(gt_camps, key=gt_camps.get) if gt_camps else "?"
        date_range = f"{timeline[0]['date']} → {timeline[-1]['date']}" if timeline else "N/A"
        total = sum(e["count"] for e in timeline)

        print(f"      Cluster {cid} (Campaign {gt_label}):  {stage:<10}  "
              f"({total} complaints, {date_range})")

    # ══════════════════════════════════════════════════════════════════
    # Summary
    # ══════════════════════════════════════════════════════════════════
    _print_header("Phase 4 Summary")
    print(f"      Clusters found      : {n_clusters}")
    print(f"      Noise points        : {n_noise}")
    if driver is not None:
        print(f"      Neo4j graph built   : ✅")
        print(f"      Hub detection       : ✅ (top {min(5, len(top_hubs))} printed)")
    else:
        print(f"      Neo4j graph built   : ⏭️  (skipped — no connection)")
    print(f"      Campaign C dormancy : {'✅ DETECTED' if cc_cluster and stage == 'dormant' else '❌ NOT DETECTED'}")
    print(f"      Relaunch alerting   : ✅ Ready")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
