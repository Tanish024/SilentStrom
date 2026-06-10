// AlertPanel.jsx — Real-time alert feed for emerging campaigns.
// Shows newly detected clusters, lifecycle stage transitions,
// and high-degree mule nodes.

import React from "react";

export default function AlertPanel() {
  // TODO: Poll /lifecycle for stage changes
  // TODO: Highlight RESURGENT campaigns and new EMERGING clusters

  return (
    <div className="alert-panel">
      <h2>⚠️ Alerts</h2>
      <ul className="alert-list">
        {/* TODO: Render alert items:
            - "Campaign X transitioned from DORMANT → RESURGENT"
            - "New cluster detected with 12 complaints"
            - "UPI mule hub ravi.kyc@ybl linked to 15 complaints"
        */}
      </ul>
    </div>
  );
}
