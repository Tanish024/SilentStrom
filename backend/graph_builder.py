"""
graph_builder.py — Neo4j mule-network graph construction for SilentStorm.

Creates the following node types:
  (:Complaint)   — one per complaint
  (:UPI)         — unique UPI IDs (hub nodes when shared across complaints)
  (:Phone)       — unique phone numbers
  (:Campaign)    — one per cluster label

Edges:
  (:Complaint)-[:USED_UPI]->(:UPI)
  (:Complaint)-[:USED_PHONE]->(:Phone)
  (:Complaint)-[:BELONGS_TO]->(:Campaign)

Hub detection:
  run_pagerank() uses Neo4j GDS PageRank when available, falling back
  to a manual degree-count approach when GDS is not installed.
"""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

# ══════════════════════════════════════════════════════════════════════
# Connection settings
# ══════════════════════════════════════════════════════════════════════

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "password123"


# ══════════════════════════════════════════════════════════════════════
# 1. Driver management
# ══════════════════════════════════════════════════════════════════════

def get_driver():
    """
    Create and return a Neo4j driver connected to bolt://localhost:7687
    with auth neo4j/password123.
    """
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


# ══════════════════════════════════════════════════════════════════════
# 2. Graph operations
# ══════════════════════════════════════════════════════════════════════

def clear_graph(driver) -> None:
    """
    DETACH DELETE all nodes in the graph — wipe everything.
    """
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("[graph_builder] ✅ Graph cleared — all nodes and relationships deleted.")


def _create_constraints(session) -> None:
    """Create uniqueness constraints for idempotent MERGE operations."""
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Complaint) REQUIRE c.id IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:UPI) REQUIRE u.address IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Phone) REQUIRE p.number IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (camp:Campaign) REQUIRE camp.label IS UNIQUE")


def ingest_complaint_to_graph(driver, complaint: dict) -> None:
    """
    Ingest a single complaint into Neo4j, creating/merging all nodes
    and relationships.

    For each complaint:
      1. MERGE a (:Complaint) node by id
      2. MERGE (:UPI) nodes by address (from entities or raw fields)
      3. MERGE (:Phone) nodes by number (from entities or raw fields)
      4. CREATE (:Complaint)-[:MENTIONS]->(:UPI) relationships
      5. CREATE (:Complaint)-[:MENTIONS]->(:Phone) relationships

    Also handles cluster/campaign linkage if 'cluster' key is present.
    """
    cid = complaint["id"]

    # Gather UPI IDs from NER-enriched entities, fallback to raw
    entities = complaint.get("entities", {})
    upi_ids = entities.get("upi_ids", complaint.get("upi_ids_raw", []))
    phones = entities.get("phones", complaint.get("phone_raw", []))

    with driver.session() as session:
        # ── Complaint node ────────────────────────────────────────────
        session.run(
            "MERGE (c:Complaint {id: $id}) "
            "SET c.text = $text, c.date = $date, "
            "    c.language = $lang, c.cluster = $cluster",
            id=cid,
            text=complaint.get("text", "")[:500],
            date=complaint.get("date", ""),
            lang=complaint.get("language", ""),
            cluster=complaint.get("cluster", -1),
        )

        # ── UPI nodes + MENTIONS edges ────────────────────────────────
        for upi in upi_ids:
            if not upi or not upi.strip():
                continue
            session.run(
                "MERGE (u:UPI {address: $addr}) "
                "WITH u "
                "MATCH (c:Complaint {id: $cid}) "
                "MERGE (c)-[:MENTIONS]->(u)",
                addr=upi.strip(),
                cid=cid,
            )

        # ── Phone nodes + MENTIONS edges ──────────────────────────────
        for phone in phones:
            if not phone or not str(phone).strip():
                continue
            session.run(
                "MERGE (p:Phone {number: $num}) "
                "WITH p "
                "MATCH (c:Complaint {id: $cid}) "
                "MERGE (c)-[:MENTIONS]->(p)",
                num=str(phone).strip(),
                cid=cid,
            )

        # ── Campaign linkage (if cluster label present) ───────────────
        cluster = complaint.get("cluster", -1)
        if cluster != -1:
            campaign_label = f"campaign_{cluster}"
            session.run(
                "MERGE (camp:Campaign {label: $label}) "
                "WITH camp "
                "MATCH (c:Complaint {id: $cid}) "
                "MERGE (c)-[:BELONGS_TO]->(camp)",
                label=campaign_label,
                cid=cid,
            )


def build_graph(
    complaints: list[dict[str, Any]],
    labels,  # np.ndarray or list of ints
) -> dict[str, int]:
    """
    Populate Neo4j with the full complaint → UPI/Phone → Campaign graph.

    This is the bulk-ingestion version: clears the graph, creates
    constraints, and ingests every complaint.

    Returns counts of created nodes and relationships.
    """
    driver = get_driver()

    # Clear previous run
    clear_graph(driver)

    with driver.session() as session:
        _create_constraints(session)

    # Track stats
    stats = {"complaints": 0, "upis": 0, "phones": 0, "campaigns": set(), "edges": 0}

    for complaint, label in zip(complaints, labels):
        label = int(label)
        complaint_with_cluster = {**complaint, "cluster": label}

        # Count entities for stats
        entities = complaint.get("entities", {})
        upi_ids = entities.get("upi_ids", complaint.get("upi_ids_raw", []))
        phones = entities.get("phones", complaint.get("phone_raw", []))

        ingest_complaint_to_graph(driver, complaint_with_cluster)

        stats["complaints"] += 1
        stats["upis"] += len(upi_ids)
        stats["phones"] += len(phones)
        stats["edges"] += len(upi_ids) + len(phones)
        if label != -1:
            stats["campaigns"].add(label)
            stats["edges"] += 1  # BELONGS_TO edge

    stats["campaigns"] = len(stats["campaigns"])

    driver.close()
    print(f"🕸️  Graph built: {stats}")
    return stats


# ══════════════════════════════════════════════════════════════════════
# 3. PageRank / Hub detection
# ══════════════════════════════════════════════════════════════════════

def run_pagerank(driver, top_n: int = 10) -> list[dict[str, Any]]:
    """
    Run PageRank on UPI and Phone nodes linked by MENTIONS relationships.

    Strategy:
      1. Try GDS PageRank (native graph projection, UNDIRECTED).
      2. If GDS plugin is not installed, fall back to manual degree counting
         (count inbound MENTIONS edges per UPI/Phone node).

    Returns:
        Top N nodes as list of dicts: [{"entity": str, "score": float}, ...]
        Sorted descending by score.
    """
    try:
        return _run_gds_pagerank(driver, top_n)
    except Exception as gds_err:
        print(f"[graph_builder] GDS PageRank unavailable ({type(gds_err).__name__}: {gds_err})")
        print("[graph_builder] Falling back to manual degree-count hub detection...")
        return _run_manual_degree_count(driver, top_n)


def _run_gds_pagerank(driver, top_n: int) -> list[dict[str, Any]]:
    """
    Run PageRank using Neo4j Graph Data Science (GDS) plugin.

    Projects UPI + Phone nodes with UNDIRECTED MENTIONS relationships,
    runs PageRank, collects results, then drops the projection.
    """
    graph_name = "silentstorm_hub_graph"

    with driver.session() as session:
        # Drop existing projection if it exists
        try:
            session.run(f"CALL gds.graph.drop('{graph_name}', false)")
        except Exception:
            pass

        # Create graph projection with UPI + Phone nodes
        # and UNDIRECTED MENTIONS relationships
        session.run(
            "CALL gds.graph.project("
            "  $name, "
            "  ['UPI', 'Phone', 'Complaint'], "
            "  {MENTIONS: {orientation: 'UNDIRECTED'}}"
            ")",
            name=graph_name,
        )

        # Run PageRank
        result = session.run(
            "CALL gds.pageRank.stream($name, {maxIterations: 20, dampingFactor: 0.85}) "
            "YIELD nodeId, score "
            "WITH gds.util.asNode(nodeId) AS node, score "
            "WHERE node:UPI OR node:Phone "
            "RETURN "
            "  CASE WHEN node:UPI THEN 'UPI:' + node.address "
            "       ELSE 'Phone:' + node.number END AS entity, "
            "  score "
            "ORDER BY score DESC "
            "LIMIT $limit",
            name=graph_name,
            limit=top_n,
        )

        results = [{"entity": r["entity"], "score": round(r["score"], 6)} for r in result]

        # Clean up projection
        session.run(f"CALL gds.graph.drop('{graph_name}', false)")

    print(f"[graph_builder] ✅ GDS PageRank complete — top {len(results)} hub nodes returned.")
    return results


def _run_manual_degree_count(driver, top_n: int) -> list[dict[str, Any]]:
    """
    Fallback hub detection: count MENTIONS edges per UPI and Phone node.

    Returns the same format as GDS PageRank:
        [{"entity": "UPI:ravi.kyc@ybl", "score": 15.0}, ...]

    Score = number of MENTIONS relationships pointing to this node.
    """
    with driver.session() as session:
        # Count MENTIONS for UPI nodes
        upi_result = session.run(
            "MATCH (c:Complaint)-[:MENTIONS]->(u:UPI) "
            "WITH u.address AS address, count(c) AS degree "
            "RETURN 'UPI:' + address AS entity, toFloat(degree) AS score "
            "ORDER BY score DESC "
            "LIMIT $limit",
            limit=top_n,
        )
        upi_hubs = [{"entity": r["entity"], "score": r["score"]} for r in upi_result]

        # Count MENTIONS for Phone nodes
        phone_result = session.run(
            "MATCH (c:Complaint)-[:MENTIONS]->(p:Phone) "
            "WITH p.number AS number, count(c) AS degree "
            "RETURN 'Phone:' + number AS entity, toFloat(degree) AS score "
            "ORDER BY score DESC "
            "LIMIT $limit",
            limit=top_n,
        )
        phone_hubs = [{"entity": r["entity"], "score": r["score"]} for r in phone_result]

    # Merge, sort, and take top N
    all_hubs = upi_hubs + phone_hubs
    all_hubs.sort(key=lambda x: x["score"], reverse=True)
    top_results = all_hubs[:top_n]

    print(f"[graph_builder] ✅ Manual degree-count complete — top {len(top_results)} hub nodes returned.")
    return top_results


# ══════════════════════════════════════════════════════════════════════
# 4. Graph export
# ══════════════════════════════════════════════════════════════════════

def export_graph() -> dict[str, Any]:
    """Export the full graph as JSON-friendly nodes + edges."""
    driver = get_driver()
    with driver.session() as session:
        nodes_result = session.run(
            "MATCH (n) RETURN id(n) AS id, labels(n) AS labels, properties(n) AS props"
        )
        edges_result = session.run(
            "MATCH (a)-[r]->(b) RETURN id(a) AS source, id(b) AS target, type(r) AS type"
        )
        nodes = [dict(r) for r in nodes_result]
        edges = [dict(r) for r in edges_result]
    driver.close()
    return {"nodes": nodes, "edges": edges}


def get_node_counts(driver) -> dict[str, int]:
    """Return count of each node label in the graph."""
    with driver.session() as session:
        result = session.run(
            "MATCH (n) "
            "RETURN labels(n)[0] AS label, count(n) AS count "
            "ORDER BY count DESC"
        )
        counts = {r["label"]: r["count"] for r in result}
    return counts
