// ClusterPanel.jsx — Side panel showing cluster details.
// Displays complaint list, shared entities, and NER-extracted data
// for a selected campaign cluster.

import React from "react";

export default function ClusterPanel({ clusterId }) {
  // TODO: Fetch /clusters/{clusterId}

  return (
    <div className="cluster-panel">
      <h2>Cluster Details</h2>
      <div className="cluster-meta">
        {/* TODO: Show cluster size, date range, lifecycle stage */}
      </div>
      <div className="shared-entities">
        {/* TODO: List top shared UPI IDs and phone numbers */}
      </div>
      <div className="complaint-list">
        {/* TODO: Scrollable list of complaint texts with highlighted entities */}
      </div>
    </div>
  );
}
