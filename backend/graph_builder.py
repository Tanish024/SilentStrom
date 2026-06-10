"""
graph_builder.py — Neo4j mule-network graph construction.

Creates the following node types:
  (:Complaint)   — one per complaint
  (:UPI)         — unique UPI IDs (hub nodes when shared across complaints)
  (:Phone)       — unique phone numbers
  (:Campaign)    — one per cluster label

Edges:
  (:Complaint)-[:USED_UPI]->(:UPI)
  (:Complaint)-[:USED_PHONE]->(:Phone)
  (:Complaint)-[:BELONGS_TO]->(:Campaign)
"""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "password123"


def get_driver():
    """Create and return a Neo4j driver."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


def build_graph(
    complaints: list[dict[str, Any]],
    labels,  # np.ndarray or list of ints
) -> dict[str, int]:
    """
    Populate Neo4j with the complaint → UPI/Phone → Campaign graph.

    Returns counts of created nodes and relationships.
    """
    driver = get_driver()

    with driver.session() as session:
        # Clear previous run
        session.run("MATCH (n) DETACH DELETE n")

        # Create constraints for idempotency
        _create_constraints(session)

        # Build nodes & edges
        stats = {"complaints": 0, "upis": 0, "phones": 0, "campaigns": 0, "edges": 0}

        for complaint, label in zip(complaints, labels):
            cid = complaint["id"]
            campaign_label = f"campaign_{label}" if label != -1 else "noise"

            # Complaint node
            session.run(
                "MERGE (c:Complaint {id: $id}) "
                "SET c.text = $text, c.date = $date, c.language = $lang, c.cluster = $cluster",
                id=cid,
                text=complaint["text"][:500],
                date=complaint.get("date", ""),
                lang=complaint.get("language", ""),
                cluster=int(label),
            )
            stats["complaints"] += 1

            # Campaign node + edge
            if label != -1:
                session.run(
                    "MERGE (camp:Campaign {label: $label}) "
                    "WITH camp "
                    "MATCH (c:Complaint {id: $cid}) "
                    "MERGE (c)-[:BELONGS_TO]->(camp)",
                    label=campaign_label,
                    cid=cid,
                )
                stats["campaigns"] += 1
                stats["edges"] += 1

            # UPI nodes + edges
            upi_ids = complaint.get("upi_ids", complaint.get("upi_ids_raw", []))
            for upi in upi_ids:
                session.run(
                    "MERGE (u:UPI {address: $addr}) "
                    "WITH u "
                    "MATCH (c:Complaint {id: $cid}) "
                    "MERGE (c)-[:USED_UPI]->(u)",
                    addr=upi,
                    cid=cid,
                )
                stats["upis"] += 1
                stats["edges"] += 1

            # Phone nodes + edges
            phones = complaint.get("phones", complaint.get("phone_raw", []))
            for phone in phones:
                session.run(
                    "MERGE (p:Phone {number: $num}) "
                    "WITH p "
                    "MATCH (c:Complaint {id: $cid}) "
                    "MERGE (c)-[:USED_PHONE]->(p)",
                    num=phone,
                    cid=cid,
                )
                stats["phones"] += 1
                stats["edges"] += 1

    driver.close()
    print(f"🕸️  Graph built: {stats}")
    return stats


def _create_constraints(session) -> None:
    """Create uniqueness constraints."""
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Complaint) REQUIRE c.id IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:UPI) REQUIRE u.address IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Phone) REQUIRE p.number IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (camp:Campaign) REQUIRE camp.label IS UNIQUE")


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
