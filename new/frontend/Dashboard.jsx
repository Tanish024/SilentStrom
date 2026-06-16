// Dashboard.jsx — Main dashboard view for SilentStorm
// Shows campaign overview, cluster stats, and alert summary.

import React from "react";

export default function Dashboard() {
  // TODO: Fetch /clusters and /lifecycle data

  return (
    <div className="dashboard">
      <h1>SilentStorm — Campaign Intelligence</h1>
      <section className="stats-grid">
        {/* TODO: Campaign count, total complaints, active alerts */}
      </section>
      <section className="campaign-cards">
        {/* TODO: Render a card per campaign cluster */}
      </section>
    </div>
  );
}
