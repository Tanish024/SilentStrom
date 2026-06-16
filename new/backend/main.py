"""
main.py — FastAPI entry-point for the SilentStorm backend.

Run with:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(
    title="SilentStorm",
    description="Fraud campaign intelligence — cluster, link, and lifecycle-track complaint waves.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Ingest ────────────────────────────────────────────────────────────
@app.post("/ingest")
async def ingest_complaints(file: UploadFile = File(...)):
    """Accept a JSON file of complaints and run the full pipeline."""
    # TODO: wire up ingest.run_pipeline(file)
    return JSONResponse(
        status_code=202,
        content={"message": "Pipeline triggered", "filename": file.filename},
    )


# ── Clusters ──────────────────────────────────────────────────────────
@app.get("/clusters")
async def list_clusters():
    """Return discovered campaign clusters with summary stats."""
    # TODO: wire up clusterer.get_clusters()
    return {"clusters": []}


@app.get("/clusters/{cluster_id}")
async def get_cluster(cluster_id: int):
    """Return details for a single cluster."""
    # TODO: wire up clusterer.get_cluster(cluster_id)
    return {"cluster_id": cluster_id, "complaints": []}


# ── Graph ─────────────────────────────────────────────────────────────
@app.get("/graph")
async def get_graph():
    """Return the mule-network graph as nodes + edges."""
    # TODO: wire up graph_builder.export_graph()
    return {"nodes": [], "edges": []}


@app.get("/graph/campaign/{campaign_label}")
async def get_campaign_graph(campaign_label: str):
    """Return subgraph for a specific campaign."""
    # TODO: wire up graph_builder.export_campaign_subgraph(campaign_label)
    return {"campaign": campaign_label, "nodes": [], "edges": []}


# ── Lifecycle ─────────────────────────────────────────────────────────
@app.get("/lifecycle")
async def get_lifecycles():
    """Return lifecycle stage for every detected campaign."""
    # TODO: wire up lifecycle.get_all()
    return {"campaigns": []}


@app.get("/lifecycle/{campaign_label}")
async def get_campaign_lifecycle(campaign_label: str):
    """Return lifecycle timeline for a single campaign."""
    # TODO: wire up lifecycle.get(campaign_label)
    return {"campaign": campaign_label, "stages": []}
