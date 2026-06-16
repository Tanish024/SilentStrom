// GraphViewer.jsx — Interactive mule-network graph visualization.
// Renders the Neo4j-sourced graph (Complaints → UPI/Phone nodes)
// to show hub mule accounts linking multiple complaints.

import React from "react";

export default function GraphViewer({ campaignId }) {
  // TODO: Fetch /graph or /graph/campaign/{campaignId}
  // TODO: Render with react-force-graph or vis.js

  return (
    <div className="graph-viewer">
      <h2>Mule Network Graph</h2>
      <div className="graph-canvas">
        {/* TODO: Force-directed graph with:
            - Blue nodes = Complaints
            - Red nodes = UPI IDs (size by degree = hub detection)
            - Green nodes = Phone numbers
            - Edges = USED_UPI / USED_PHONE relationships
        */}
      </div>
      <div className="graph-controls">
        {/* TODO: Zoom, filter by node type, highlight hubs */}
      </div>
    </div>
  );
}
