// CampaignTimeline.jsx — Temporal view of campaign complaint waves.
// Renders a timeline/chart showing complaint volume over time per campaign,
// with dormancy gaps highlighted.

import React from "react";

export default function CampaignTimeline({ campaignId }) {
  // TODO: Fetch /lifecycle/{campaignId} data
  // TODO: Render timeline with d3 or recharts

  return (
    <div className="campaign-timeline">
      <h2>Campaign Timeline</h2>
      <div className="timeline-chart">
        {/* TODO: Render date-based complaint heatmap / line chart */}
        {/* TODO: Highlight DORMANT gaps with a different color band */}
      </div>
      <div className="lifecycle-badge">
        {/* TODO: Show EMERGING / ACTIVE / DORMANT / RESURGENT / DECLINED badge */}
      </div>
    </div>
  );
}
