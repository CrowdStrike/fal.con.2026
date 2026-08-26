import { useState, useEffect, useContext } from "react";
import { FalconApiContext } from "../contexts/falcon-api-context";

export default function DriftAlerts() {
  const { falcon } = useContext(FalconApiContext);
  const [auditEvents, setAuditEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [timeRange, setTimeRange] = useState(null);
  const [filterPolicyType, setFilterPolicyType] = useState("all");
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [showEventDialog, setShowEventDialog] = useState(false);
  const [creatingSnapshot, setCreatingSnapshot] = useState(false);

  const createSnapshot = async () => {
    setCreatingSnapshot(true);
    try {
      const result = await falcon
        .cloudFunction({ name: "snapshot-manager" })
        .path("/api/snapshot/create")
        .post({
          snapshot_type: "manual",
          description: "Manual snapshot for drift detection"
        });

      if (result.statusCode === 200) {
        // Refresh drift events after creating snapshot
        await fetchAuditEvents(selectedDays, filterPolicyType);
      } else {
        setError("Failed to create snapshot");
      }
    } catch (err) {
      console.error("Error creating snapshot:", err);
      setError("Failed to create snapshot: " + err.message);
    } finally {
      setCreatingSnapshot(false);
    }
  };

  const fetchAuditEvents = async (days = 7, policyType = "all") => {
    setLoading(true);
    setError(null);

    try {
      // First, get list of snapshots
      const snapshotsResult = await falcon
        .cloudFunction({ name: "snapshot-manager" })
        .path("/api/snapshot/list?limit=10")
        .get();

      if (snapshotsResult.statusCode !== 200 || !snapshotsResult.body.snapshots || snapshotsResult.body.snapshots.length < 2) {
        setError("Need at least 2 snapshots to detect drift. Create snapshots to track policy changes.");
        setLoading(false);
        return;
      }

      const snapshots = snapshotsResult.body.snapshots;

      // Compare most recent with previous
      const currentSnapshot = snapshots[0];
      const baselineSnapshot = snapshots[1];

      // Detect drift between snapshots
      const driftResult = await falcon
        .cloudFunction({ name: "drift-detector" })
        .path("/api/drift/detect")
        .post({
          baseline_snapshot_id: baselineSnapshot.snapshot_id,
          current_snapshot_id: currentSnapshot.snapshot_id
        });

      if (driftResult.statusCode === 200) {
        let events = driftResult.body.drift_events || [];

        // Filter by policy type if needed
        if (policyType !== "all") {
          events = events.filter(e => e.policy_type === policyType);
        }

        setAuditEvents(events);
        setSummary(driftResult.body.summary || null);
        setTimeRange({
          start: baselineSnapshot.timestamp,
          end: currentSnapshot.timestamp,
          days: "Snapshot comparison"
        });
      } else {
        setError("Failed to detect drift between snapshots");
      }
    } catch (err) {
      console.error("Error fetching drift events:", err);
      setError(err.message || "Failed to fetch drift events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log("Drift Alerts page loaded - v1.3.5");
    fetchAuditEvents(7, filterPolicyType);
  }, [filterPolicyType]);

  const handleEventClick = (event) => {
    setSelectedEvent(event);
    setShowEventDialog(true);
  };

  const getRiskBadgeVariant = (riskLevel) => {
    switch (riskLevel) {
      case "CRITICAL":
        return "danger";
      case "HIGH":
        return "warning";
      case "MEDIUM":
        return "primary";
      case "LOW":
        return "success";
      default:
        return "neutral";
    }
  };

  const getDriftTypeBadge = (driftType) => {
    const badges = {
      added: { variant: "success", text: "Added" },
      removed: { variant: "danger", text: "Removed" },
      modified: { variant: "primary", text: "Modified" },
      enabled: { variant: "success", text: "Enabled" },
      disabled: { variant: "danger", text: "Disabled" },
    };
    return badges[driftType] || { variant: "neutral", text: driftType };
  };

  const formatDateTime = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return timestamp;
    }
  };

  return (
    <div style={{ padding: "20px", maxWidth: "1400px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ margin: "0 0 8px 0", fontSize: "28px", fontWeight: "600" }}>
          🔔 Drift Alerts
        </h1>
        <p style={{ margin: 0, color: "var(--sl-color-neutral-600)" }}>
          Policy changes detected by comparing snapshots over time
        </p>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "16px",
            marginBottom: "24px",
          }}
        >
          <sl-card style={{ padding: "16px" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "32px", fontWeight: "700", color: "var(--sl-color-danger-600)" }}>
                {summary.critical || 0}
              </div>
              <div style={{ color: "var(--sl-color-neutral-600)", fontSize: "14px" }}>Critical</div>
            </div>
          </sl-card>

          <sl-card style={{ padding: "16px" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "32px", fontWeight: "700", color: "var(--sl-color-warning-600)" }}>
                {summary.high || 0}
              </div>
              <div style={{ color: "var(--sl-color-neutral-600)", fontSize: "14px" }}>High Risk</div>
            </div>
          </sl-card>

          <sl-card style={{ padding: "16px" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "32px", fontWeight: "700", color: "var(--sl-color-primary-600)" }}>
                {summary.medium || 0}
              </div>
              <div style={{ color: "var(--sl-color-neutral-600)", fontSize: "14px" }}>Medium Risk</div>
            </div>
          </sl-card>

          <sl-card style={{ padding: "16px" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "32px", fontWeight: "700", color: "var(--sl-color-success-600)" }}>
                {summary.low || 0}
              </div>
              <div style={{ color: "var(--sl-color-neutral-600)", fontSize: "14px" }}>Low Risk</div>
            </div>
          </sl-card>

          <sl-card style={{ padding: "16px" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "32px", fontWeight: "700" }}>
                {auditEvents.length}
              </div>
              <div style={{ color: "var(--sl-color-neutral-600)", fontSize: "14px" }}>Total Events</div>
            </div>
          </sl-card>
        </div>
      )}

      {/* Filters */}
      <sl-card style={{ marginBottom: "20px", padding: "16px" }}>
        <div style={{ display: "flex", gap: "16px", alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ flex: "0 0 auto" }}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "14px", fontWeight: "500" }}>
              Policy Type
            </label>
            <sl-select
              value={filterPolicyType}
              onSlChange={(e) => setFilterPolicyType(e.target.value)}
              style={{ minWidth: "150px" }}
            >
              <sl-option value="all">All Types</sl-option>
              <sl-option value="prevention">Prevention</sl-option>
              <sl-option value="response">Response</sl-option>
              <sl-option value="firewall">Firewall</sl-option>
            </sl-select>
          </div>

          <div style={{ flex: "1 1 auto", textAlign: "right", display: "flex", gap: "8px", justifyContent: "flex-end" }}>
            <sl-button
              variant="default"
              onClick={createSnapshot}
              loading={creatingSnapshot}
            >
              📸 Create Snapshot
            </sl-button>
            <sl-button
              variant="primary"
              onClick={() => fetchAuditEvents(7, filterPolicyType)}
              loading={loading}
            >
              🔄 Refresh
            </sl-button>
          </div>
        </div>

        {timeRange && (
          <div style={{ marginTop: "12px", fontSize: "13px", color: "var(--sl-color-neutral-600)" }}>
            Comparing snapshots: {formatDateTime(timeRange.start)} to {formatDateTime(timeRange.end)}
          </div>
        )}
      </sl-card>

      {/* Loading State */}
      {loading && (
        <sl-card style={{ padding: "40px", textAlign: "center" }}>
          <sl-spinner style={{ fontSize: "48px" }}></sl-spinner>
          <p style={{ marginTop: "16px" }}>Loading audit events...</p>
        </sl-card>
      )}

      {/* Error State */}
      {error && !loading && (
        <sl-alert variant="danger" open>
          <strong>Error</strong>
          <br />
          {error}
        </sl-alert>
      )}

      {/* Events Table */}
      {!loading && !error && auditEvents.length > 0 && (
        <sl-card>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                  <th style={{ padding: "12px", textAlign: "left", fontWeight: "600" }}>Timestamp</th>
                  <th style={{ padding: "12px", textAlign: "left", fontWeight: "600" }}>Policy Name</th>
                  <th style={{ padding: "12px", textAlign: "center", fontWeight: "600" }}>Type</th>
                  <th style={{ padding: "12px", textAlign: "center", fontWeight: "600" }}>Change</th>
                  <th style={{ padding: "12px", textAlign: "center", fontWeight: "600" }}>Risk</th>
                  <th style={{ padding: "12px", textAlign: "left", fontWeight: "600" }}>User</th>
                  <th style={{ padding: "12px", textAlign: "center", fontWeight: "600" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {auditEvents.map((event, idx) => {
                  const driftBadge = getDriftTypeBadge(event.drift_type);
                  return (
                    <tr
                      key={event.event_id || idx}
                      style={{
                        borderBottom: "1px solid var(--sl-color-neutral-200)",
                        cursor: "pointer",
                        transition: "background-color 0.2s",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--sl-color-neutral-50)")}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                      onClick={() => handleEventClick(event)}
                    >
                      <td style={{ padding: "12px", fontSize: "13px" }}>
                        {formatDateTime(event.detected_at)}
                      </td>
                      <td style={{ padding: "12px", fontWeight: "500" }}>
                        {event.policy_name}
                      </td>
                      <td style={{ padding: "12px", textAlign: "center" }}>
                        <sl-badge variant="neutral" pill>
                          {event.policy_type}
                        </sl-badge>
                      </td>
                      <td style={{ padding: "12px", textAlign: "center" }}>
                        <sl-badge variant={driftBadge.variant} pill>
                          {driftBadge.text}
                        </sl-badge>
                      </td>
                      <td style={{ padding: "12px", textAlign: "center" }}>
                        <sl-badge variant={getRiskBadgeVariant(event.risk_level)} pill>
                          {event.risk_level}
                        </sl-badge>
                      </td>
                      <td style={{ padding: "12px", fontSize: "13px" }}>
                        {event.user_name || "Unknown"}
                      </td>
                      <td style={{ padding: "12px", textAlign: "center" }}>
                        <sl-button size="small" variant="text">
                          View Details
                        </sl-button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </sl-card>
      )}

      {/* Empty State */}
      {!loading && !error && auditEvents.length === 0 && (
        <sl-card style={{ padding: "40px", textAlign: "center" }}>
          <div style={{ fontSize: "48px", marginBottom: "16px" }}>✅</div>
          <h3 style={{ margin: "0 0 8px 0" }}>No Policy Changes Detected</h3>
          <p style={{ color: "var(--sl-color-neutral-600)", margin: "0 0 16px 0" }}>
            No drift detected between the last two snapshots.
          </p>
          <sl-button variant="primary" onClick={createSnapshot} loading={creatingSnapshot}>
            📸 Create New Snapshot
          </sl-button>
        </sl-card>
      )}

      {/* Event Details Dialog */}
      {selectedEvent && (
        <sl-dialog
          label="📋 Event Details"
          open={showEventDialog}
          onSlAfterHide={() => setShowEventDialog(false)}
          style={{ "--width": "700px" }}
        >
          <div style={{ padding: "8px 0" }}>
            {/* Event Header */}
            <div style={{ marginBottom: "20px", paddingBottom: "16px", borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
              <h3 style={{ margin: "0 0 8px 0", fontSize: "18px" }}>
                {selectedEvent.policy_name}
              </h3>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <sl-badge variant="neutral">{selectedEvent.policy_type}</sl-badge>
                <sl-badge variant={getDriftTypeBadge(selectedEvent.drift_type).variant}>
                  {getDriftTypeBadge(selectedEvent.drift_type).text}
                </sl-badge>
                <sl-badge variant={getRiskBadgeVariant(selectedEvent.risk_level)}>
                  {selectedEvent.risk_level}
                </sl-badge>
              </div>
            </div>

            {/* Event Info */}
            <div style={{ display: "grid", gap: "16px" }}>
              <div>
                <div style={{ fontSize: "12px", fontWeight: "600", color: "var(--sl-color-neutral-600)", marginBottom: "4px" }}>
                  TIMESTAMP
                </div>
                <div>{formatDateTime(selectedEvent.detected_at)}</div>
              </div>

              <div>
                <div style={{ fontSize: "12px", fontWeight: "600", color: "var(--sl-color-neutral-600)", marginBottom: "4px" }}>
                  USER
                </div>
                <div>{selectedEvent.user_name || "Unknown"}</div>
                {selectedEvent.user_id && (
                  <div style={{ fontSize: "12px", color: "var(--sl-color-neutral-600)" }}>
                    ID: {selectedEvent.user_id}
                  </div>
                )}
              </div>

              <div>
                <div style={{ fontSize: "12px", fontWeight: "600", color: "var(--sl-color-neutral-600)", marginBottom: "4px" }}>
                  ACTION
                </div>
                <div style={{ fontFamily: "monospace", fontSize: "13px" }}>
                  {selectedEvent.action_name}
                </div>
              </div>

              <div>
                <div style={{ fontSize: "12px", fontWeight: "600", color: "var(--sl-color-neutral-600)", marginBottom: "4px" }}>
                  POLICY ID
                </div>
                <div style={{ fontFamily: "monospace", fontSize: "13px" }}>
                  {selectedEvent.policy_id}
                </div>
              </div>

              {selectedEvent.description && (
                <div>
                  <div style={{ fontSize: "12px", fontWeight: "600", color: "var(--sl-color-neutral-600)", marginBottom: "4px" }}>
                    DESCRIPTION
                  </div>
                  <div>{selectedEvent.description}</div>
                </div>
              )}

              {selectedEvent.changes && (
                <div>
                  <div style={{ fontSize: "12px", fontWeight: "600", color: "var(--sl-color-neutral-600)", marginBottom: "4px" }}>
                    CHANGES
                  </div>
                  <div
                    style={{
                      backgroundColor: "var(--sl-color-neutral-50)",
                      padding: "12px",
                      borderRadius: "4px",
                      fontFamily: "monospace",
                      fontSize: "12px",
                      overflowX: "auto",
                    }}
                  >
                    <pre style={{ margin: 0 }}>{JSON.stringify(selectedEvent.changes, null, 2)}</pre>
                  </div>
                </div>
              )}

              <div>
                <div style={{ fontSize: "12px", fontWeight: "600", color: "var(--sl-color-neutral-600)", marginBottom: "4px" }}>
                  RISK SCORE
                </div>
                <div>
                  <sl-progress-bar
                    value={selectedEvent.risk_score || 0}
                    style={{ "--height": "20px" }}
                  ></sl-progress-bar>
                  <div style={{ marginTop: "4px", fontSize: "13px" }}>
                    {selectedEvent.risk_score}/100
                  </div>
                </div>
              </div>
            </div>
          </div>

          <sl-button slot="footer" variant="primary" onClick={() => setShowEventDialog(false)}>
            Close
          </sl-button>
        </sl-dialog>
      )}
    </div>
  );
}
