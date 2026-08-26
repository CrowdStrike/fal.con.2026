import React, { useContext, useState, useEffect } from "react";
import { FalconApiContext } from "../contexts/falcon-api-context";
import { setBasePath } from '@shoelace-style/shoelace/dist/utilities/base-path.js';
import "@shoelace-style/shoelace/dist/components/card/card.js";
import "@shoelace-style/shoelace/dist/components/button/button.js";
import "@shoelace-style/shoelace/dist/components/spinner/spinner.js";
import "@shoelace-style/shoelace/dist/components/badge/badge.js";
import "@shoelace-style/shoelace/dist/components/alert/alert.js";
import "@shoelace-style/shoelace/dist/components/tab-group/tab-group.js";
import "@shoelace-style/shoelace/dist/components/tab/tab.js";
import "@shoelace-style/shoelace/dist/components/tab-panel/tab-panel.js";
import "@shoelace-style/shoelace/dist/components/icon/icon.js";
import "@shoelace-style/shoelace/dist/components/progress-ring/progress-ring.js";
import "@shoelace-style/shoelace/dist/components/dialog/dialog.js";
import "@shoelace-style/shoelace/dist/components/details/details.js";

// Set Shoelace to use CDN for icons (allowed by CSP)
setBasePath('https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.19.1/cdn/');

// Documentation links per module key
const MODULE_DOCS = {
  prevent: "https://docs.crowdstrike.com/",
  insight: "https://falcon.crowdstrike.com/documentation/85/edr-detection-details",
  firewall: "https://falcon.crowdstrike.com/documentation/87/falcon-firewall-management",
  device_control: "https://falcon.crowdstrike.com/documentation/65/device-control",
  spotlight: "https://falcon.crowdstrike.com/documentation/70/spotlight-vulnerability-management",
  identity: "https://falcon.crowdstrike.com/documentation/128/falcon-identity-threat-detection",
};

// Documentation links per prevention setting ID
const PREVENTION_DOCS = {
  SensorTamperingProtection: "https://docs.crowdstrike.com/",
  CloudAntiMalware: "https://docs.crowdstrike.com/",
  OnSensorMLSlider: "https://docs.crowdstrike.com/",
  AdwarePUP: "https://docs.crowdstrike.com/",
  NextGenAV: "https://docs.crowdstrike.com/",
  ScriptBasedExecutionMonitoring: "https://docs.crowdstrike.com/",
  InterpreterProtection: "https://docs.crowdstrike.com/",
  EnhancedExploitationVisibility: "https://docs.crowdstrike.com/",
  PreventSuspiciousProcesses: "https://docs.crowdstrike.com/",
  MaliciousPowershell: "https://docs.crowdstrike.com/",
  SuspiciousRegistryOperations: "https://docs.crowdstrike.com/",
  SuspiciousKernelDrivers: "https://docs.crowdstrike.com/",
  VolumeShadowCopyProtect: "https://docs.crowdstrike.com/",
  QuarantineOnWrite: "https://docs.crowdstrike.com/",
  default: "https://docs.crowdstrike.com/",
};


function Home() {
  const { falcon } = useContext(FalconApiContext);
  const [healthData, setHealthData] = useState(null);
  const [sensorHealth, setSensorHealth] = useState(null);
  const [adoptionData, setAdoptionData] = useState(null);
  const [operationsData, setOperationsData] = useState(null);
  const [discoverUtilization, setDiscoverUtilization] = useState(null);
  const [hostHealthData, setHostHealthData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sensorLoading, setSensorLoading] = useState(false);
  const [adoptionLoading, setAdoptionLoading] = useState(false);
  const [operationsLoading, setOperationsLoading] = useState(false);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [hostHealthLoading, setHostHealthLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sensorError, setSensorError] = useState(null);
  const [adoptionError, setAdoptionError] = useState(null);
  const [operationsError, setOperationsError] = useState(null);
  const [discoverError, setDiscoverError] = useState(null);
  const [hostHealthError, setHostHealthError] = useState(null);
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [showPolicyDialog, setShowPolicyDialog] = useState(false);
  const [snapshots, setSnapshots] = useState([]);
  const [snapshotsLoading, setSnapshotsLoading] = useState(false);
  const [driftData, setDriftData] = useState(null);
  const [driftLoading, setDriftLoading] = useState(false);
  const [applyingBestPractices, setApplyingBestPractices] = useState({});
  const [applyResult, setApplyResult] = useState(null);
  const [showSnapshotDialog, setShowSnapshotDialog] = useState(false);
  const [showDriftDialog, setShowDriftDialog] = useState(false);

  const handlePolicyClick = (policy) => {
    setSelectedPolicy(policy);
    setApplyResult(null);
    setShowPolicyDialog(true);
  };

  const fetchHealthCheck = async () => {
    setLoading(true);
    setError(null);
    try {
      // Use cloudFunction method to call the Foundry function
      const config = {
        name: 'policy-checker',
        version: 4  // Specify version from manifest
      };
      const healthCheckFn = falcon.cloudFunction(config);
      const response = await healthCheckFn.path('/api/health/check').post({});

      console.log('Full response:', JSON.stringify(response, null, 2));

      if (response.status_code !== 200) {
        const errorDetails = JSON.stringify(response.errors || response, null, 2);
        console.error('Function error details:', errorDetails);
        throw new Error(`Function call failed (${response.status_code}): ${errorDetails}`);
      }

      if (response && response.body) {
        setHealthData(response.body);
      } else {
        setError("No data returned from health check");
      }
    } catch (err) {
      console.error('Health check error:', err);
      const errorDetails = JSON.stringify(err.errors || err, null, 2);
      const errorMessages = err.errors?.map(e => e.message || JSON.stringify(e)).join(', ');
      setError(`Error: ${errorMessages || err.message || errorDetails || "An error occurred"}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchSensorHealth = async () => {
    setSensorLoading(true);
    setSensorError(null);
    try {
      const sensorHealthFn = falcon.cloudFunction({ name: 'sensor-health' });
      const response = await sensorHealthFn.path('/api/sensors/health').get();

      console.log('Sensor Health Full Response:', JSON.stringify(response, null, 2));

      if (response.status_code !== 200) {
        const errorDetails = JSON.stringify(response.errors || response, null, 2);
        console.error('Sensor health error details:', errorDetails);
        const errorMessages = response.errors?.map(e => e.message || JSON.stringify(e)).join(', ');
        throw new Error(`Sensor health check failed (${response.status_code}): ${errorMessages || errorDetails}`);
      }

      if (response && response.body) {
        setSensorHealth(response.body);
      } else {
        setSensorError("No sensor data returned");
      }
    } catch (err) {
      console.error('Sensor health check error:', err);
      setSensorError(err.message || "Failed to fetch sensor health");
    } finally {
      setSensorLoading(false);
    }
  };

  const fetchAdoptionData = async () => {
    setAdoptionLoading(true);
    setAdoptionError(null);
    try {
      const adoptionFn = falcon.cloudFunction({ name: 'module-adoption-checker' });
      const response = await adoptionFn.path('/api/adoption/check').get();

      console.log('Adoption Check Response:', JSON.stringify(response, null, 2));

      if (response.status_code !== 200) {
        const errorDetails = JSON.stringify(response.errors || response, null, 2);
        console.error('Adoption check error details:', errorDetails);
        throw new Error(`Adoption check failed (${response.status_code}): ${errorDetails}`);
      }

      if (response && response.body) {
        setAdoptionData(response.body);
      } else {
        setAdoptionError("No adoption data returned");
      }
    } catch (err) {
      console.error('Adoption check error:', err);
      const errorMessages = err.errors?.map(e => e.message || JSON.stringify(e)).join(', ');
      setAdoptionError(`Error: ${errorMessages || err.message || "An error occurred"}`);
    } finally {
      setAdoptionLoading(false);
    }
  };

  const fetchOperationsData = async () => {
    setOperationsLoading(true);
    setOperationsError(null);
    try {
      const operationsFn = falcon.cloudFunction({ name: 'operations-metrics' });
      const response = await operationsFn.path('/api/operations/metrics').get();

      console.log('Operations Metrics Response:', JSON.stringify(response, null, 2));

      if (response.status_code !== 200) {
        const errorDetails = JSON.stringify(response.errors || response, null, 2);
        console.error('Operations metrics error details:', errorDetails);
        throw new Error(`Operations metrics failed (${response.status_code}): ${errorDetails}`);
      }

      if (response && response.body) {
        setOperationsData(response.body);
      } else {
        setOperationsError("No operations data returned");
      }
    } catch (err) {
      console.error('Operations metrics error:', err);
      const errorMessages = err.errors?.map(e => e.message || JSON.stringify(e)).join(', ');
      setOperationsError(`Error: ${errorMessages || err.message || "An error occurred"}`);
    } finally {
      setOperationsLoading(false);
    }
  };

  const checkDiscoverUtilization = async () => {
    setDiscoverLoading(true);
    setDiscoverError(null);
    try {
      const discoverFn = falcon.cloudFunction({ name: 'module-adoption-checker' });
      const response = await discoverFn.path('/api/adoption/discover-utilization').get();

      console.log('Discover Utilization Response:', JSON.stringify(response, null, 2));

      if (response.status_code !== 200) {
        const errorDetails = JSON.stringify(response.errors || response, null, 2);
        console.error('Discover utilization error details:', errorDetails);
        throw new Error(`Discover utilization check failed (${response.status_code}): ${errorDetails}`);
      }

      if (response && response.body) {
        setDiscoverUtilization(response.body);
      } else {
        setDiscoverError("No Discover utilization data returned");
      }
    } catch (err) {
      console.error('Discover utilization error:', err);
      const errorMessages = err.errors?.map(e => e.message || JSON.stringify(e)).join(', ');
      setDiscoverError(`Error: ${errorMessages || err.message || "An error occurred"}`);
    } finally {
      setDiscoverLoading(false);
    }
  };

  const fetchHostHealth = async () => {
    setHostHealthLoading(true);
    setHostHealthError(null);
    try {
      const config = {
        name: 'host-health-checker',
        version: 1
      };
      const hostHealthFn = falcon.cloudFunction(config);
      const response = await hostHealthFn.path('/api/hosts/health').post({});

      console.log('Host Health Response:', JSON.stringify(response, null, 2));

      if (response.status_code !== 200) {
        const errorDetails = JSON.stringify(response.errors || response, null, 2);
        console.error('Host health error details:', errorDetails);
        throw new Error(`Host health check failed (${response.status_code}): ${errorDetails}`);
      }

      if (response && response.body) {
        setHostHealthData(response.body);
      } else {
        setHostHealthError("No host health data returned");
      }
    } catch (err) {
      console.error('Host health error:', err);
      const errorMessages = err.errors?.map(e => e.message || JSON.stringify(e)).join(', ');
      setHostHealthError(`Error: ${errorMessages || err.message || "An error occurred"}`);
    } finally {
      setHostHealthLoading(false);
    }
  };

  const applyBestPractices = async (policyId, policyName, dryRun = false) => {
    setApplyingBestPractices(prev => ({ ...prev, [policyId]: true }));
    try {
      const policyCheckerFn = falcon.cloudFunction({ name: 'policy-checker' });
      const response = await policyCheckerFn.path('/api/policy/apply-best-practices').post({
        policy_id: policyId,
        dry_run: dryRun,
        settings_to_apply: ['all']
      });

      if (response.status_code !== 200) {
        const errorMsg = response.errors?.map(e => e.message).join(', ') || `Failed (${response.status_code})`;
        setApplyResult({ success: false, message: errorMsg });
        return;
      }

      if (response.body) {
        const result = response.body;
        setApplyResult({
          success: true,
          changes_made: result.changes_made,
          compliance_before: result.compliance_before,
          compliance_after: result.compliance_after,
        });
        // Don't auto-refresh — let user close and refresh manually to avoid state conflicts
      }
    } catch (err) {
      setApplyResult({ success: false, message: err.message || 'Unknown error' });
    } finally {
      setApplyingBestPractices(prev => {
        const next = { ...prev };
        delete next[policyId];
        return next;
      });
    }
  };

  const testPolicyChange = async (policyId, policyName) => {
    setTestingPolicy(prev => ({ ...prev, [policyId]: true }));
    try {
      const policyCheckerFn = falcon.cloudFunction({ name: 'policy-checker' });
      const response = await policyCheckerFn.path('/api/policy/test-change').post({
        policy_id: policyId
      });

      console.log('🧪 Test policy change response:', response);

      if (response.status_code !== 200) {
        const errorMsg = response.errors?.map(e => e.message).join(', ') || `Failed (${response.status_code})`;
        alert(`❌ Test failed for ${policyName}:\n${errorMsg}`);
        throw new Error(errorMsg);
      }

      if (response.body) {
        const result = response.body;
        alert(`✅ TEST SUCCESS for ${policyName}!\n\n` +
              `Setting: ${result.setting_changed}\n` +
              `Old Value: ${result.old_value}\n` +
              `New Value: ${result.new_value}\n\n` +
              `This confirms we can modify policies!`);
        console.log('✅ Test successful:', result);
        // Refresh health check to show the change
        fetchHealthCheck();
      }
    } catch (err) {
      console.error('🧪 Test policy change error:', err);
      console.error('Error details:', JSON.stringify(err, null, 2));
    } finally {
      setTestingPolicy(prev => ({ ...prev, [policyId]: false }));
    }
  };

  const createSnapshot = async (snapshotType = 'manual', description = '') => {
    setSnapshotsLoading(true);
    try {
      const snapshotFn = falcon.cloudFunction({ name: 'snapshot-manager' });
      const response = await snapshotFn.path('/api/snapshot/create').post({
        snapshot_type: snapshotType,
        description: description
      });

      console.log('Create snapshot response:', response);

      if (response.status_code !== 200) {
        const errorMsg = response.errors?.map(e => e.message).join(', ') || `Failed (${response.status_code})`;
        throw new Error(errorMsg);
      }

      if (response.body) {
        console.log(`✅ Snapshot created: ${response.body.snapshot_id}`);
        console.log(`Total policies: ${response.body.total_policies}`);
        fetchSnapshots(); // Refresh snapshot list
      }
    } catch (err) {
      console.error('Create snapshot error:', err);
      console.error('Error details:', JSON.stringify(err, null, 2));
    } finally {
      setSnapshotsLoading(false);
    }
  };

  const fetchSnapshots = async () => {
    setSnapshotsLoading(true);
    try {
      const snapshotFn = falcon.cloudFunction({ name: 'snapshot-manager' });
      const response = await snapshotFn.path('/api/snapshot/list').get();

      if (response.status_code === 200 && response.body) {
        setSnapshots(response.body.snapshots || []);
      }
    } catch (err) {
      console.error('Fetch snapshots error:', err);
    } finally {
      setSnapshotsLoading(false);
    }
  };

  const detectDrift = async (baselineSnapshotId, currentSnapshotId) => {
    setDriftLoading(true);
    try {
      const driftFn = falcon.cloudFunction({ name: 'drift-detector' });
      const response = await driftFn.path('/api/drift/detect').post({
        baseline_snapshot_id: baselineSnapshotId,
        current_snapshot_id: currentSnapshotId
      });

      console.log('Drift detection response:', response);

      if (response.status_code !== 200) {
        const errorMsg = response.errors?.map(e => e.message).join(', ') || `Failed (${response.status_code})`;
        throw new Error(errorMsg);
      }

      if (response.body) {
        setDriftData(response.body);
        setShowDriftDialog(true);
      }
    } catch (err) {
      console.error('Detect drift error:', err);
      console.error('Error details:', JSON.stringify(err, null, 2));
    } finally {
      setDriftLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthCheck();
    fetchSensorHealth();
    fetchAdoptionData();
    fetchOperationsData();
    fetchHostHealth();
    fetchSnapshots(); // Load snapshots on mount
  }, []);

  const getStatusVariant = (status) => {
    const statusMap = {
      Excellent: "success",
      Good: "primary",
      Fair: "warning",
      "Needs Attention": "warning",
      Critical: "danger",
    };
    return statusMap[status] || "neutral";
  };

  const getScoreColor = (score) => {
    if (score >= 90) return "#10b981";
    if (score >= 80) return "#3b82f6";
    if (score >= 70) return "#f59e0b";
    if (score >= 60) return "#f97316";
    return "#ef4444";
  };

  const getAdoptionVariant = (level) => {
    const variantMap = {
      Excellent: "success",
      Good: "primary",
      Partial: "warning",
      "Needs Attention": "warning",
      Inactive: "danger",
      "Scope Required": "neutral",
      "Not Available": "neutral",
      Error: "danger"
    };
    return variantMap[level] || "neutral";
  };

  const getHostHealthVariant = (issueCount) => {
    if (issueCount === 0) return "success";
    if (issueCount <= 5) return "primary";
    if (issueCount <= 15) return "warning";
    return "danger";
  };

  const getModuleIcon = (moduleKey) => {
    const iconMap = {
      prevent: "shield-fill-check",
      insight: "eye-fill",
      firewall: "fire",
      discover: "search",
      device_control: "usb-symbol",
      identity_protection: "person-badge",
      fusion: "gear-wide-connected",
      overwatch: "binoculars-fill"
    };
    return iconMap[moduleKey] || "grid";
  };

  return (
    <div style={{ padding: "24px", maxWidth: "1400px", margin: "0 auto" }}>
      {/* Header - Centered */}
      <div style={{ marginBottom: "32px", textAlign: "center" }}>
        <h1 style={{ fontSize: "32px", fontWeight: "bold", marginBottom: "8px", color: "var(--sl-color-neutral-900)" }}>
          🛡️ Falcon Health Check
        </h1>
        <p style={{ color: "var(--sl-color-neutral-600)", fontSize: "18px" }}>
          Monitor your CrowdStrike Falcon policies and detect configuration drift
        </p>
      </div>

      {/* Action Bar */}
      <div style={{ marginBottom: "24px", display: "flex", gap: "12px", alignItems: "center" }}>
        <span onClick={fetchHealthCheck} style={{ cursor: loading ? "not-allowed" : "pointer" }}>
          <sl-button variant="primary" size="large" disabled={loading}>
            {loading ? (
              <><sl-spinner slot="prefix"></sl-spinner>Checking...</>
            ) : (
              <><sl-icon slot="prefix" name="arrow-clockwise"></sl-icon>Run Health Check</>
            )}
          </sl-button>
        </span>
        {healthData && (
          <span style={{ fontSize: "15px", color: "var(--sl-color-neutral-500)" }}>
            Last run: {new Date(healthData.timestamp).toLocaleString()}
          </span>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <sl-alert variant="danger" open style={{ marginBottom: "24px" }}>
          <strong>⚠️ Error:</strong> {error}
        </sl-alert>
      )}

      {/* Loading State */}
      {loading && !healthData && (
        <div style={{ textAlign: "center", padding: "60px" }}>
          <sl-spinner style={{ fontSize: "48px" }}></sl-spinner>
          <p style={{ marginTop: "16px", color: "#64748b" }}>
            Analyzing your Falcon policies...
          </p>
        </div>
      )}

      {/* Health Dashboard */}
      {healthData && (
        <>
          {/* Overview Cards */}
          {(() => {
            const prevPolicies = healthData.prevention?.policies || [];
            const avgCompliance = prevPolicies.length > 0
              ? Math.round(prevPolicies.reduce((s, p) => s + (p.analysis?.compliance_percentage || 0), 0) / prevPolicies.length)
              : 0;
            const coveredSensors = prevPolicies.reduce((s, p) => s + (p.analysis?.sensor_count || 0), 0);
            const totalSensors = healthData.summary?.total_sensors || 0;
            const uncoveredSensors = Math.max(0, totalSensors - coveredSensors);
            const coveragePct = totalSensors > 0 ? Math.round((coveredSensors / totalSensors) * 100) : 0;
            const criticalIssues = prevPolicies.reduce((s, p) => s + (p.analysis?.critical_issues || 0), 0);
            const highIssues = prevPolicies.reduce((s, p) => s + (p.analysis?.high_issues || 0), 0);
            const cardLabel = { fontSize: "17px", fontWeight: "600", color: "var(--sl-color-neutral-600)", marginBottom: "10px", textTransform: "uppercase", letterSpacing: "0.5px" };
            const cardValue = { fontSize: "44px", fontWeight: "700", lineHeight: 1, marginBottom: "12px" };
            const cardSub = { fontSize: "16px", color: "var(--sl-color-neutral-600)", lineHeight: "1.8" };
            const cardStyle = { "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" };
            const pad = { padding: "24px" };

            return (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "20px", marginBottom: "32px" }}>

                {/* Health Score */}
                <sl-card style={cardStyle}>
                  <div style={{ ...pad, textAlign: "center" }}>
                    <div style={cardLabel}>Health Score</div>
                    <sl-progress-ring
                      value={healthData.overall_score}
                      style={{ "--size": "130px", "--track-width": "12px", "--indicator-color": getScoreColor(healthData.overall_score), "--track-color": "var(--sl-color-neutral-200)", fontSize: "36px", fontWeight: "700", color: "var(--sl-color-neutral-900)" }}
                    >
                      {Math.round(healthData.overall_score)}
                    </sl-progress-ring>
                    <div style={{ marginTop: "14px" }}>
                      <sl-badge variant={getStatusVariant(healthData.overall_status)} pill style={{ fontSize: "16px", padding: "6px 14px" }}>
                        {healthData.overall_status}
                      </sl-badge>
                    </div>
                    {healthData.score_breakdown && (
                      <div style={{ marginTop: "14px", fontSize: "16px", color: "var(--sl-color-neutral-600)", textAlign: "left", borderTop: "1px solid var(--sl-color-neutral-200)", paddingTop: "12px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}><span>Compliance</span><strong>{healthData.score_breakdown.prevention_compliance}%</strong></div>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}><span>Coverage</span><strong>{healthData.score_breakdown.sensor_coverage}%</strong></div>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}><span>RFM-free</span><strong>{healthData.score_breakdown.rfm_free}%</strong></div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}><span>Issues</span><strong>{healthData.score_breakdown.issues_score}%</strong></div>
                      </div>
                    )}
                  </div>
                </sl-card>

                {/* Sensor Coverage */}
                <sl-card style={cardStyle}>
                  <div style={pad}>
                    <div style={cardLabel}>Sensor Coverage</div>
                    <div style={{ ...cardValue, color: coveragePct >= 90 ? "var(--sl-color-success-600)" : coveragePct >= 70 ? "var(--sl-color-warning-600)" : "var(--sl-color-danger-600)" }}>
                      {totalSensors > 0 ? `${coveragePct}%` : "—"}
                    </div>
                    <div style={cardSub}>
                      <div>Total sensors: <strong>{totalSensors}</strong></div>
                      <div>With policy: <strong>{coveredSensors}</strong></div>
                      {uncoveredSensors > 0 && (
                        <div style={{ color: "var(--sl-color-warning-600)", fontWeight: "600" }}>
                          No policy: {uncoveredSensors}
                        </div>
                      )}
                    </div>
                  </div>
                </sl-card>

                {/* Prevention Compliance */}
                <sl-card style={cardStyle}>
                  <div style={pad}>
                    <div style={cardLabel}>Avg Compliance</div>
                    <div style={{ ...cardValue, color: avgCompliance >= 90 ? "var(--sl-color-success-600)" : avgCompliance >= 70 ? "var(--sl-color-warning-600)" : "var(--sl-color-danger-600)" }}>
                      {avgCompliance}%
                    </div>
                    <div style={cardSub}>
                      <div>Prevention policies: <strong>{prevPolicies.length}</strong></div>
                      <div>At 100%: <strong>{prevPolicies.filter(p => (p.analysis?.compliance_percentage || 0) === 100).length}</strong></div>
                      <div>Below 100%: <strong>{prevPolicies.filter(p => (p.analysis?.compliance_percentage || 0) < 100).length}</strong></div>
                    </div>
                  </div>
                </sl-card>

                {/* Issues */}
                <sl-card style={cardStyle}>
                  <div style={pad}>
                    <div style={cardLabel}>Policy Issues</div>
                    <div style={{ ...cardValue, color: (criticalIssues + highIssues) > 0 ? "var(--sl-color-danger-600)" : "var(--sl-color-success-600)" }}>
                      {criticalIssues + highIssues}
                    </div>
                    <div style={cardSub}>
                      <div>Critical: <strong style={{ color: criticalIssues > 0 ? "var(--sl-color-danger-600)" : "inherit" }}>{criticalIssues}</strong></div>
                      <div>High: <strong style={{ color: highIssues > 0 ? "var(--sl-color-warning-600)" : "inherit" }}>{highIssues}</strong></div>
                      <div>Total policies: <strong>{healthData.total_policies}</strong></div>
                    </div>
                  </div>
                </sl-card>

              </div>
            );
          })()}

          {/* Sensor Health Section */}
          {sensorHealth && (
            <div style={{ marginBottom: "32px" }}>
              <h2 style={{ fontSize: "20px", fontWeight: "600", marginBottom: "16px", color: "var(--sl-color-neutral-900)" }}>
                💻 Sensor Health
              </h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
                {/* Total Sensors */}
                {sensorHealth && sensorHealth.summary && (
                  <sl-card style={{
                    "--border-radius": "var(--sl-border-radius-large)",
                    boxShadow: "var(--sl-shadow-large)"
                  }}>
                    <div style={{ padding: "16px" }}>
                      <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginBottom: "6px", fontWeight: "500" }}>
                        Total Sensors
                      </div>
                      <div style={{ fontSize: "32px", fontWeight: "bold", color: "var(--sl-color-neutral-900)" }}>
                        {sensorHealth.summary.total_sensors}
                      </div>
                      <div style={{ fontSize: "16px", color: "var(--sl-color-success-600)", marginTop: "4px", fontWeight: "500" }}>
                        ✓ {sensorHealth.summary.active_sensors} active
                      </div>
                    </div>
                  </sl-card>
                )}

                {/* Inactive Sensors */}
                {sensorHealth && sensorHealth.summary && (
                  <sl-card style={{
                    "--border-radius": "var(--sl-border-radius-large)",
                    boxShadow: "var(--sl-shadow-large)"
                  }}>
                    <div style={{ padding: "16px" }}>
                      <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginBottom: "6px", fontWeight: "500" }}>
                        Inactive Sensors
                      </div>
                      <div style={{ fontSize: "32px", fontWeight: "bold", color: sensorHealth.summary.inactive_sensors > 0 ? "var(--sl-color-warning-600)" : "var(--sl-color-success-600)" }}>
                        {sensorHealth.summary.inactive_sensors}
                      </div>
                      <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginTop: "4px", fontWeight: "500" }}>
                        14+ days offline
                      </div>
                    </div>
                  </sl-card>
                )}

                {/* RFM Sensors */}
                <sl-card style={{
                  "--border-radius": "var(--sl-border-radius-large)",
                  boxShadow: "var(--sl-shadow-large)"
                }}>
                  <div style={{ padding: "16px" }}>
                    <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginBottom: "6px", fontWeight: "500" }}>
                      RFM Sensors
                    </div>
                    <div style={{ fontSize: "32px", fontWeight: "bold", color: sensorHealth.summary.rfm_sensors > 0 ? "var(--sl-color-danger-600)" : "var(--sl-color-success-600)" }}>
                      {sensorHealth.summary.rfm_sensors}
                    </div>
                    <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginTop: "4px", fontWeight: "500" }}>
                      Reduced Functionality
                    </div>
                  </div>
                </sl-card>

                {/* Platform Breakdown */}
                <sl-card style={{
                  "--border-radius": "var(--sl-border-radius-large)",
                  boxShadow: "var(--sl-shadow-large)"
                }}>
                  <div style={{ padding: "20px" }}>
                    <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginBottom: "16px", fontWeight: "600" }}>
                      Platform Breakdown
                    </div>
                    {Object.entries(sensorHealth.platform_breakdown).map(([platform, stats]) => (
                      <div key={platform} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                        <span style={{ fontSize: "16px", color: "var(--sl-color-neutral-900)", fontWeight: "500" }}>{platform}</span>
                        <sl-badge variant="neutral" pill>{stats.count} sensors</sl-badge>
                      </div>
                    ))}
                  </div>
                </sl-card>
              </div>

              {/* Sensor Issues */}
              {sensorHealth.top_issues && sensorHealth.top_issues.length > 0 && (
                <sl-alert variant="warning" open style={{ marginTop: "20px" }}>
                  <strong>⚠️ Sensor Issues Detected:</strong>
                  <ul style={{ marginTop: "8px", marginBottom: "0" }}>
                    {sensorHealth.top_issues.map((issue, idx) => (
                      <li key={idx}>
                        <strong>[{issue.severity}]</strong> {issue.issue} - <em>{issue.recommendation}</em>
                      </li>
                    ))}
                  </ul>
                </sl-alert>
              )}
            </div>
          )}

          {/* Sensor Loading State */}
          {sensorLoading && !sensorHealth && (
            <div style={{ marginBottom: "32px", textAlign: "center", padding: "40px" }}>
              <sl-spinner style={{ fontSize: "32px" }}></sl-spinner>
              <p style={{ marginTop: "12px", color: "#64748b" }}>Loading sensor health...</p>
            </div>
          )}

          {/* Sensor Error */}
          {sensorError && (
            <sl-alert variant="warning" open style={{ marginBottom: "32px" }}>
              <strong>Sensor Health:</strong> {sensorError}
            </sl-alert>
          )}

          {/* Detailed Tabs */}
          <sl-tab-group>
            <sl-tab slot="nav" panel="prevention">
              <sl-icon name="shield-fill-check"></sl-icon>
              Prevention Policies
              {healthData && healthData.prevention && healthData.prevention.health && (
                <sl-badge variant={getStatusVariant(healthData.prevention.health.status)} pill>
                  {Math.round(healthData.prevention.health.score)}
                </sl-badge>
              )}
            </sl-tab>
            <sl-tab slot="nav" panel="response">
              <sl-icon name="lightning-fill"></sl-icon>
              Response Policies
              {healthData && healthData.response && healthData.response.health && (
                <sl-badge variant={getStatusVariant(healthData.response.health.status)} pill>
                  {Math.round(healthData.response.health.score)}
                </sl-badge>
              )}
            </sl-tab>
            <sl-tab slot="nav" panel="firewall">
              <sl-icon name="fire"></sl-icon>
              Firewall Policies
              {healthData && healthData.firewall && healthData.firewall.health && (
                <sl-badge variant={getStatusVariant(healthData.firewall.health.status)} pill>
                  {Math.round(healthData.firewall.health.score)}
                </sl-badge>
              )}
            </sl-tab>
            <sl-tab slot="nav" panel="adoption">
              <sl-icon name="bar-chart-fill"></sl-icon>
              Module Adoption
              {adoptionData && (
                <sl-badge variant={getAdoptionVariant(adoptionData.overall_level)} pill>
                  {Math.round(adoptionData.overall_score)}
                </sl-badge>
              )}
            </sl-tab>
            <sl-tab slot="nav" panel="operations">
              <sl-icon name="gear-wide-connected"></sl-icon>
              Operations
              {operationsData && operationsData.summary && (
                <sl-badge variant={operationsData.summary.critical_issues.length === 0 ? "success" : "warning"} pill>
                  {operationsData.summary.critical_issues.length === 0 ? "✓" : operationsData.summary.critical_issues.length}
                </sl-badge>
              )}
            </sl-tab>
            <sl-tab slot="nav" panel="host-health">
              <sl-icon name="shield-exclamation"></sl-icon>
              Host Health
              {hostHealthData && hostHealthData.overall_health && (
                <sl-badge variant={getHostHealthVariant(hostHealthData.overall_health.total_issues)} pill>
                  {hostHealthData.overall_health.total_issues}
                </sl-badge>
              )}
            </sl-tab>

            {/* Prevention Panel */}
            <sl-tab-panel name="prevention">
              {healthData && healthData.prevention && healthData.prevention.health && healthData.prevention.policies && (
                <div style={{ marginTop: "20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                    <h3 style={{ fontSize: "26px", fontWeight: "600" }}>Prevention Policies</h3>
                    <sl-badge variant={getStatusVariant(healthData.prevention.health.status)} pill style={{ fontSize: "20px", padding: "10px 18px" }}>
                      {healthData.prevention.health.enabled_count} / {healthData.prevention.health.total_count} Enabled
                    </sl-badge>
                  </div>

                  {/* Snapshot and Drift Controls */}
                  <div style={{ marginBottom: "20px", display: "flex", gap: "12px", alignItems: "center", padding: "14px 16px", background: "var(--sl-color-neutral-50)", borderRadius: "8px", border: "1px solid var(--sl-color-neutral-200)" }}>
                    <sl-button
                      size="medium"
                      variant="default"
                      onClick={() => createSnapshot('manual', 'Manual snapshot from dashboard')}
                      loading={snapshotsLoading}
                    >
                      <sl-icon slot="prefix" name="camera"></sl-icon>
                      Create Snapshot
                    </sl-button>
                    <span
                      onClick={() => snapshots.length >= 1 && setShowSnapshotDialog(true)}
                      style={{ cursor: snapshots.length >= 1 ? "pointer" : "not-allowed" }}
                    >
                      <sl-button
                        size="medium"
                        variant="default"
                        disabled={snapshots.length < 1}
                      >
                        <sl-icon slot="prefix" name="file-diff"></sl-icon>
                        Check Drift ({snapshots.length} snapshots)
                      </sl-button>
                    </span>
                    <div style={{ marginLeft: "auto", fontSize: "17px", color: "var(--sl-color-neutral-600)" }}>
                      {snapshots.length > 0 && (
                        <span>Last snapshot: {new Date(snapshots[0]?.timestamp).toLocaleString()}</span>
                      )}
                    </div>
                  </div>

                  {/* Policies Table */}
                  <div style={{ overflow: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                          <th style={{ padding: "14px", textAlign: "left", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "18px" }}>Policy Name</th>
                          <th style={{ padding: "14px", textAlign: "left", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "18px" }}>Platform</th>
                          <th style={{ padding: "14px", textAlign: "center", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "18px" }}>Status</th>
                          <th style={{ padding: "14px", textAlign: "center", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "18px" }}>Compliance</th>
                          <th style={{ padding: "14px", textAlign: "center", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "18px" }}>Coverage</th>
                          <th style={{ padding: "14px", textAlign: "center", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "18px" }}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {healthData.prevention.policies.map((policy, idx) => (
                        <tr
                          key={idx}
                          style={{
                            borderBottom: "1px solid var(--sl-color-neutral-200)",
                            cursor: "pointer",
                            transition: "background 0.2s"
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = "var(--sl-color-neutral-50)"}
                          onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                        >
                          <td style={{ padding: "14px", fontWeight: "500", color: "var(--sl-color-neutral-900)", fontSize: "18px" }}>{policy.name}</td>
                          <td style={{ padding: "14px", color: "var(--sl-color-neutral-700)", fontSize: "17px" }}>
                            <sl-badge variant="neutral">{policy.platform}</sl-badge>
                          </td>
                          <td style={{ padding: "14px", textAlign: "center" }}>
                            <sl-badge variant={policy.enabled ? "success" : "neutral"} pill style={{ fontSize: "15px" }}>
                              {policy.enabled ? "✓ Enabled" : "Disabled"}
                            </sl-badge>
                          </td>
                          <td style={{ padding: "14px", textAlign: "center" }}>
                            {policy.analysis && policy.analysis.compliance_percentage !== undefined ? (
                              <sl-badge
                                variant={
                                  policy.analysis.compliance_percentage >= 90 ? "success" :
                                  policy.analysis.compliance_percentage >= 75 ? "primary" :
                                  policy.analysis.compliance_percentage >= 50 ? "warning" : "danger"
                                }
                                pill
                                style={{ fontSize: "15px" }}
                              >
                                {policy.analysis.compliance_percentage}%
                              </sl-badge>
                            ) : (
                              <sl-badge variant="neutral" style={{ fontSize: "15px" }}>N/A</sl-badge>
                            )}
                          </td>
                          <td style={{ padding: "14px", textAlign: "center" }}>
                            {policy.analysis && policy.analysis.coverage_percentage !== undefined ? (
                              <div>
                                <sl-badge
                                  variant={
                                    policy.analysis.coverage_percentage >= 90 ? "success" :
                                    policy.analysis.coverage_percentage >= 70 ? "warning" : "danger"
                                  }
                                  pill
                                  style={{ fontSize: "15px" }}
                                >
                                  {policy.analysis.coverage_percentage}%
                                </sl-badge>
                                <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-500)", marginTop: "2px" }}>
                                  {policy.analysis.sensor_count || 0} sensors
                                </div>
                              </div>
                            ) : (
                              <sl-badge variant="neutral">N/A</sl-badge>
                            )}
                          </td>
                          <td style={{ padding: "12px", textAlign: "center" }}>
                            <span onClick={() => handlePolicyClick(policy)} style={{ cursor: "pointer" }}>
                              <sl-button size="small" variant="primary">
                                View Details
                              </sl-button>
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              )}
            </sl-tab-panel>

            {/* Response Panel */}
            <sl-tab-panel name="response">
              {healthData && healthData.response && healthData.response.health && healthData.response.policies && (
                <div style={{ marginTop: "20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                    <h3 style={{ fontSize: "20px", fontWeight: "600" }}>Response Policies</h3>
                    <sl-badge variant={getStatusVariant(healthData.response.health.status)} pill style={{ fontSize: "16px", padding: "8px 16px" }}>
                      {healthData.response.health.enabled_count} / {healthData.response.health.total_count} Enabled
                    </sl-badge>
                  </div>

                  <div style={{ overflow: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                          <th style={{ padding: "13px", textAlign: "left", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "17px" }}>Policy Name</th>
                          <th style={{ padding: "13px", textAlign: "left", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "17px" }}>Platform</th>
                          <th style={{ padding: "13px", textAlign: "center", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "17px" }}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {healthData.response.policies.map((policy, idx) => (
                        <tr key={idx} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                          <td style={{ padding: "13px", fontWeight: "500", color: "var(--sl-color-neutral-900)", fontSize: "17px" }}>{policy.name}</td>
                          <td style={{ padding: "13px", color: "var(--sl-color-neutral-700)", fontSize: "17px" }}>
                            <sl-badge variant="neutral">{policy.platform}</sl-badge>
                          </td>
                          <td style={{ padding: "13px", textAlign: "center" }}>
                            <sl-badge variant={policy.enabled ? "success" : "neutral"} pill>
                              {policy.enabled ? "✓ Enabled" : "Disabled"}
                            </sl-badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              )}
            </sl-tab-panel>

            {/* Firewall Panel */}
            <sl-tab-panel name="firewall">
              {healthData && healthData.firewall && healthData.firewall.health && healthData.firewall.policies && (
                <div style={{ marginTop: "20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                    <h3 style={{ fontSize: "20px", fontWeight: "600" }}>Firewall Policies</h3>
                    <sl-badge variant={getStatusVariant(healthData.firewall.health.status)} pill style={{ fontSize: "16px", padding: "8px 16px" }}>
                      {healthData.firewall.health.enabled_count} / {healthData.firewall.health.total_count} Enabled
                    </sl-badge>
                  </div>

                  <div style={{ overflow: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                        <th style={{ padding: "13px", textAlign: "left", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "17px" }}>Policy Name</th>
                        <th style={{ padding: "13px", textAlign: "left", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "17px" }}>Platform</th>
                        <th style={{ padding: "13px", textAlign: "center", fontWeight: "600", color: "var(--sl-color-neutral-700)", fontSize: "17px" }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {healthData.firewall.policies.map((policy, idx) => (
                        <tr key={idx} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                          <td style={{ padding: "13px", fontWeight: "500", color: "var(--sl-color-neutral-900)", fontSize: "17px" }}>{policy.name}</td>
                          <td style={{ padding: "13px", color: "var(--sl-color-neutral-700)", fontSize: "17px" }}>
                            <sl-badge variant="neutral">{policy.platform}</sl-badge>
                          </td>
                          <td style={{ padding: "13px", textAlign: "center" }}>
                            <sl-badge variant={policy.enabled ? "success" : "neutral"} pill>
                              {policy.enabled ? "✓ Enabled" : "Disabled"}
                            </sl-badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              )}
            </sl-tab-panel>

            {/* Module Adoption Panel */}
            <sl-tab-panel name="adoption">
              <div style={{ marginTop: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                  <h3 style={{ fontSize: "20px", fontWeight: "600", color: "var(--sl-color-neutral-900)" }}>📊 Module Adoption Scorecard</h3>
                  <sl-button variant="primary" size="small" onClick={fetchAdoptionData} disabled={adoptionLoading}>
                    {adoptionLoading ? (
                      <>
                        <sl-spinner slot="prefix"></sl-spinner>
                        Checking...
                      </>
                    ) : (
                      <>
                        <sl-icon slot="prefix" name="arrow-clockwise"></sl-icon>
                        Refresh
                      </>
                    )}
                  </sl-button>
                </div>

                {adoptionError && (
                  <sl-alert variant="danger" open style={{ marginBottom: "24px" }}>
                    <strong>⚠️ Error:</strong> {adoptionError}
                  </sl-alert>
                )}

                {adoptionLoading && !adoptionData && (
                  <div style={{ textAlign: "center", padding: "60px" }}>
                    <sl-spinner style={{ fontSize: "48px" }}></sl-spinner>
                    <p style={{ marginTop: "16px", color: "var(--sl-color-neutral-600)" }}>
                      Checking module adoption...
                    </p>
                  </div>
                )}

                {adoptionData && (
                  <>
                    {/* Summary Stats */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "24px" }}>
                      {/* Overall Score */}
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ textAlign: "center", padding: "16px" }}>
                          <div style={{ fontSize: "16px", fontWeight: "500", marginBottom: "12px", color: "var(--sl-color-neutral-600)" }}>
                            Overall Score
                          </div>
                          <sl-progress-ring
                            value={adoptionData.overall_score}
                            style={{
                              "--size": "80px",
                              "--track-width": "8px",
                              "--indicator-color": getScoreColor(adoptionData.overall_score),
                              "--track-color": "var(--sl-color-neutral-200)",
                              fontSize: "24px",
                              fontWeight: "bold",
                              color: "var(--sl-color-neutral-900)"
                            }}
                          >
                            {Math.round(adoptionData.overall_score)}
                          </sl-progress-ring>
                          <div style={{ marginTop: "12px" }}>
                            <sl-badge variant={getAdoptionVariant(adoptionData.overall_level)} pill style={{ fontSize: "15px" }}>
                              {adoptionData.overall_level}
                            </sl-badge>
                          </div>
                        </div>
                      </sl-card>

                      {/* Scored Modules */}
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginBottom: "6px", fontWeight: "500" }}>
                            Analyzed Modules
                          </div>
                          <div style={{ fontSize: "28px", fontWeight: "bold", color: "var(--sl-color-success-600)" }}>
                            {adoptionData.scored_module_count || 0}
                          </div>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginTop: "4px" }}>
                            With adoption scores
                          </div>
                        </div>
                      </sl-card>

                      {/* Additional Modules */}
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginBottom: "6px", fontWeight: "500" }}>
                            Additional Modules
                          </div>
                          <div style={{ fontSize: "28px", fontWeight: "bold", color: "var(--sl-color-neutral-600)" }}>
                            {adoptionData.additional_module_count || 0}
                          </div>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginTop: "4px" }}>
                            Licensed in your CID
                          </div>
                        </div>
                      </sl-card>

                      {/* Total */}
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginBottom: "6px", fontWeight: "500" }}>
                            Total Modules
                          </div>
                          <div style={{ fontSize: "28px", fontWeight: "bold", color: "var(--sl-color-primary-600)" }}>
                            {adoptionData.total_module_count || 0}
                          </div>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginTop: "4px" }}>
                            In your environment
                          </div>
                        </div>
                      </sl-card>
                    </div>

                    {/* Scored Modules Section */}
                    {adoptionData.modules.filter(m => m.scored).length > 0 && (
                      <>
                        <h4 style={{ fontSize: "18px", fontWeight: "600", marginBottom: "12px", color: "var(--sl-color-neutral-900)" }}>
                          📊 Analyzed Modules (with Adoption Scores)
                        </h4>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))", gap: "16px", marginBottom: "24px" }}>
                          {adoptionData.modules.filter(m => m.scored).map((module) => (
                            <sl-card key={module.module_key} style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                              <div style={{ padding: "16px" }}>
                                {/* Module Header */}
                                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
                                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                    <sl-icon name={getModuleIcon(module.module_key)} style={{ fontSize: "24px", color: "var(--sl-color-primary-600)" }}></sl-icon>
                                    <div>
                                      <div style={{ fontSize: "16px", fontWeight: "600", color: "var(--sl-color-neutral-900)" }}>
                                        {module.module_name}
                                      </div>
                                      <sl-badge variant={getAdoptionVariant(module.adoption_level)} pill size="small">
                                        {module.adoption_level}
                                      </sl-badge>
                                    </div>
                                  </div>
                                  {module.adoption_score !== null && (
                                    <div style={{ fontSize: "20px", fontWeight: "bold", color: getScoreColor(module.adoption_score) }}>
                                      {Math.round(module.adoption_score)}
                                    </div>
                                  )}
                                </div>

                                {/* Progress Bar */}
                                {module.adoption_score !== null && (
                                  <sl-progress-bar
                                    value={module.adoption_score}
                                    style={{
                                      "--height": "6px",
                                      "--indicator-color": getScoreColor(module.adoption_score),
                                      "--track-color": "var(--sl-color-neutral-200)",
                                      marginBottom: "12px"
                                    }}
                                  ></sl-progress-bar>
                                )}

                                {/* Features Checklist */}
                                {module.features && module.features.length > 0 && (
                                  <div style={{ marginBottom: "12px" }}>
                                    {module.features.map((feature, idx) => (
                                      <div key={idx} style={{ display: "flex", alignItems: "start", gap: "8px", padding: "6px 0", borderBottom: idx < module.features.length - 1 ? "1px solid var(--sl-color-neutral-200)" : "none" }}>
                                        <sl-icon
                                          name={feature.enabled ? "check-circle-fill" : "x-circle-fill"}
                                          style={{
                                            fontSize: "18px",
                                            color: feature.enabled ? "var(--sl-color-success-600)" : "var(--sl-color-danger-600)",
                                            marginTop: "2px",
                                            flexShrink: 0
                                          }}
                                        ></sl-icon>
                                        <div style={{ flex: 1 }}>
                                          <div style={{ fontSize: "15px", fontWeight: "500", color: "var(--sl-color-neutral-900)" }}>
                                            {feature.feature_name}
                                          </div>
                                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginTop: "2px" }}>
                                            {feature.detail}
                                          </div>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {/* Recommendation + Doc Link */}
                                {module.top_recommendation && (
                                  <sl-alert variant="neutral" open style={{ marginTop: "10px", fontSize: "16px" }}>
                                    <sl-icon slot="icon" name="lightbulb-fill"></sl-icon>
                                    <strong>Tip:</strong> {module.top_recommendation}
                                    {MODULE_DOCS[module.module_key] && (
                                      <> — <span onClick={() => (window.top || window).open(MODULE_DOCS[module.module_key], "_blank")} style={{ color: "var(--sl-color-primary-600)", cursor: "pointer" }}>View Docs ↗</span></>
                                    )}
                                  </sl-alert>
                                )}
                              </div>
                            </sl-card>
                          ))}
                        </div>
                      </>
                    )}

                    {/* Additional Licensed Modules Section */}
                    {adoptionData.modules.filter(m => !m.scored).length > 0 && (
                      <>
                        <h4 style={{ fontSize: "18px", fontWeight: "600", marginBottom: "12px", color: "var(--sl-color-neutral-900)" }}>
                          📦 Additional Licensed Modules - Platform Utilization
                        </h4>
                        <sl-alert variant="primary" open style={{ marginBottom: "16px" }}>
                          <sl-icon slot="icon" name="info-circle-fill"></sl-icon>
                          <strong>Note:</strong> These modules are licensed in your CID but don't have automated adoption scoring yet. For best results connecting with CrowdStrike team, here are a few things you can verify yourself:
                          <ul style={{ marginTop: "8px", marginBottom: 0, paddingLeft: "20px", fontSize: "15px" }}>
                            <li>Click "Check Utilization" on modules that support it to verify active usage</li>
                            <li>Review their configuration manually in the Falcon console</li>
                            <li>Check if data is flowing and being actively reviewed</li>
                          </ul>
                        </sl-alert>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "12px", marginBottom: "24px" }}>
                          {adoptionData.modules.filter(m => !m.scored).map((module) => (
                            <sl-card key={module.module_key} style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-medium)" }}>
                              <div style={{ padding: "12px" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                                  <sl-icon name={module.icon || "grid"} style={{ fontSize: "20px", color: "var(--sl-color-neutral-600)" }}></sl-icon>
                                  <div style={{ flex: 1 }}>
                                    <div style={{ fontSize: "15px", fontWeight: "600", color: "var(--sl-color-neutral-900)" }}>
                                      {module.module_name}
                                    </div>
                                    <sl-badge variant="neutral" pill size="small">Licensed</sl-badge>
                                  </div>
                                </div>

                                {/* Show Check Utilization button for Falcon Discover */}
                                {module.module_key === 'discover' && (
                                  <div style={{ marginTop: "12px" }}>
                                    <sl-button
                                      variant="primary"
                                      size="small"
                                      onClick={checkDiscoverUtilization}
                                      disabled={discoverLoading}
                                      style={{ width: "100%" }}
                                    >
                                      {discoverLoading ? (
                                        <>
                                          <sl-spinner slot="prefix" style={{ fontSize: "16px" }}></sl-spinner>
                                          Checking...
                                        </>
                                      ) : (
                                        <>
                                          <sl-icon slot="prefix" name="play-circle"></sl-icon>
                                          Check Utilization
                                        </>
                                      )}
                                    </sl-button>

                                    {/* Show utilization results */}
                                    {discoverUtilization && (
                                      <div style={{ marginTop: "12px", padding: "12px", background: "var(--sl-color-neutral-50)", borderRadius: "6px" }}>
                                        <div style={{ fontSize: "16px", fontWeight: "600", marginBottom: "8px", color: "var(--sl-color-neutral-900)" }}>
                                          Utilization:
                                          <sl-badge
                                            variant={
                                              discoverUtilization.utilization_status === "Excellent" ? "success" :
                                              discoverUtilization.utilization_status === "Good" ? "primary" :
                                              discoverUtilization.utilization_status === "Partial" || discoverUtilization.utilization_status === "Low" ? "warning" :
                                              "danger"
                                            }
                                            pill
                                            style={{ marginLeft: "8px" }}
                                          >
                                            {discoverUtilization.has_been_reviewed ? `${discoverUtilization.utilization_percentage}%` : "0%"}
                                          </sl-badge>
                                        </div>
                                        <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-700)", marginBottom: "8px" }}>
                                          📊 Total Assets: {discoverUtilization.total_hosts}<br/>
                                          ✅ Reviewed: {discoverUtilization.reviewed_count}<br/>
                                          ⚠️ Unreviewed: {discoverUtilization.unreviewed_count}<br/>
                                          {discoverUtilization.unmanaged_count > 0 && (
                                            <>🔍 Unmanaged: {discoverUtilization.unmanaged_count}<br/></>
                                          )}
                                        </div>
                                        <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-700)", fontStyle: "italic", marginTop: "8px", paddingTop: "8px", borderTop: "1px solid var(--sl-color-neutral-200)" }}>
                                          {discoverUtilization.recommendation}
                                        </div>
                                      </div>
                                    )}

                                    {discoverError && (
                                      <sl-alert variant="danger" open style={{ marginTop: "12px", fontSize: "15px" }}>
                                        {discoverError}
                                      </sl-alert>
                                    )}
                                  </div>
                                )}

                                {/* Default message for other modules */}
                                {module.module_key !== 'discover' && (
                                  <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginTop: "8px" }}>
                                    Manual review recommended
                                  </div>
                                )}
                              </div>
                            </sl-card>
                          ))}
                        </div>
                      </>
                    )}

                    {/* Top Recommendations */}
                    {adoptionData.modules.some(m => m.scored && m.adoption_score !== null && m.adoption_score < 80) && (
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <h4 style={{ fontSize: "18px", fontWeight: "600", marginBottom: "12px", color: "var(--sl-color-neutral-900)" }}>
                            🎯 Actions to Improve Adoption
                          </h4>
                          <ol style={{ margin: 0, paddingLeft: "20px", fontSize: "15px" }}>
                            {adoptionData.modules
                              .filter(m => m.scored && m.adoption_score !== null && m.adoption_score < 80)
                              .sort((a, b) => a.adoption_score - b.adoption_score)
                              .map((module, idx) => (
                                <li key={idx} style={{ marginBottom: "8px", color: "var(--sl-color-neutral-900)" }}>
                                  <strong>{module.module_name}:</strong> {module.top_recommendation}
                                </li>
                              ))}
                          </ol>
                        </div>
                      </sl-card>
                    )}
                  </>
                )}
              </div>
            </sl-tab-panel>

            {/* Operations Tab Panel */}
            <sl-tab-panel name="operations">
              <div style={{ marginTop: "20px" }}>
                {operationsLoading && (
                  <div style={{ textAlign: "center", padding: "40px" }}>
                    <sl-spinner style={{ fontSize: "48px", "--track-width": "8px" }}></sl-spinner>
                    <p style={{ marginTop: "16px", color: "var(--sl-color-neutral-600)" }}>Loading operational metrics...</p>
                  </div>
                )}

                {operationsError && (
                  <sl-alert variant="danger" open>
                    <sl-icon slot="icon" name="exclamation-triangle-fill"></sl-icon>
                    <strong>Operations Metrics Error:</strong> {operationsError}
                  </sl-alert>
                )}

                {operationsData && (
                  <>
                    {/* Summary Stats */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "16px", marginBottom: "24px" }}>
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginBottom: "8px" }}>🛡️ Uninstall Protection Rate</div>
                          <div style={{ fontSize: "32px", fontWeight: "bold", color: "var(--sl-color-primary-600)" }}>
                            {operationsData.summary.protection_rate}%
                          </div>
                          <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginTop: "4px" }}>
                            {operationsData.uninstall_protection.protected} / {operationsData.uninstall_protection.total} hosts protected
                          </div>
                        </div>
                      </sl-card>

                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginBottom: "8px" }}>📅 Version Currency Rate</div>
                          <div style={{ fontSize: "32px", fontWeight: "bold", color: "var(--sl-color-success-600)" }}>
                            {operationsData.summary.currency_rate}%
                          </div>
                          <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginTop: "4px" }}>
                            {operationsData.version_currency.age_categories["N (Current)"]} / {operationsData.version_currency.total_hosts} on current version
                          </div>
                        </div>
                      </sl-card>

                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginBottom: "8px" }}>📋 Policy Assignment Rate</div>
                          <div style={{ fontSize: "32px", fontWeight: "bold", color: "var(--sl-color-primary-600)" }}>
                            {operationsData.summary.assignment_rate}%
                          </div>
                          <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginTop: "4px" }}>
                            {operationsData.policy_assignments.assigned} / {operationsData.policy_assignments.total_hosts} hosts assigned
                          </div>
                        </div>
                      </sl-card>

                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginBottom: "8px" }}>⚠️ EOL/Unsupported Hosts</div>
                          <div style={{ fontSize: "32px", fontWeight: "bold", color: operationsData.summary.eol_host_count > 0 ? "var(--sl-color-danger-600)" : "var(--sl-color-success-600)" }}>
                            {operationsData.summary.eol_host_count}
                          </div>
                          <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginTop: "4px" }}>
                            Hosts on N-4+ versions
                          </div>
                        </div>
                      </sl-card>
                    </div>

                    {/* Critical Issues Alert */}
                    {operationsData.summary.critical_issues.length > 0 && (
                      <sl-alert variant="warning" open style={{ marginBottom: "24px" }}>
                        <sl-icon slot="icon" name="exclamation-triangle-fill"></sl-icon>
                        <strong>Critical Issues Detected:</strong>
                        <ul style={{ marginTop: "8px", marginBottom: 0, paddingLeft: "20px" }}>
                          {operationsData.summary.critical_issues.map((issue, idx) => (
                            <li key={idx}>{issue}</li>
                          ))}
                        </ul>
                      </sl-alert>
                    )}

                    {/* Uninstall Protection by Platform */}
                    <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)", marginBottom: "24px" }}>
                      <div slot="header" style={{ fontSize: "18px", fontWeight: "600", color: "var(--sl-color-neutral-900)" }}>
                        🛡️ Uninstall Protection by Platform
                      </div>
                      <div style={{ padding: "16px" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                          <thead>
                            <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Platform</th>
                              <th style={{ padding: "12px", textAlign: "right", fontWeight: "600", fontSize: "15px" }}>Total Hosts</th>
                              <th style={{ padding: "12px", textAlign: "right", fontWeight: "600", fontSize: "15px" }}>Protected</th>
                              <th style={{ padding: "12px", textAlign: "right", fontWeight: "600", fontSize: "15px" }}>Unprotected</th>
                              <th style={{ padding: "12px", textAlign: "right", fontWeight: "600", fontSize: "15px" }}>Protection Rate</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(operationsData.uninstall_protection.by_platform).map(([platform, stats]) => (
                              <tr key={platform} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                                <td style={{ padding: "12px", fontSize: "15px" }}>{platform}</td>
                                <td style={{ padding: "12px", textAlign: "right", fontSize: "15px" }}>{stats.total}</td>
                                <td style={{ padding: "12px", textAlign: "right", fontSize: "15px", color: "var(--sl-color-success-600)" }}>
                                  {stats.protected}
                                </td>
                                <td style={{ padding: "12px", textAlign: "right", fontSize: "15px", color: stats.unprotected > 0 ? "var(--sl-color-danger-600)" : "var(--sl-color-neutral-600)" }}>
                                  {stats.unprotected}
                                </td>
                                <td style={{ padding: "12px", textAlign: "right", fontSize: "15px" }}>
                                  <sl-badge variant={stats.protection_rate >= 95 ? "success" : stats.protection_rate >= 80 ? "warning" : "danger"} pill>
                                    {stats.protection_rate}%
                                  </sl-badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </sl-card>

                    {/* Version Currency by Platform */}
                    <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)", marginBottom: "24px" }}>
                      <div slot="header" style={{ fontSize: "18px", fontWeight: "600", color: "var(--sl-color-neutral-900)" }}>
                        📅 Sensor Version Age Distribution
                      </div>
                      <div style={{ padding: "16px" }}>
                        {/* Overall Age Categories */}
                        <div style={{ marginBottom: "24px" }}>
                          <h4 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "12px" }}>Overall Distribution</h4>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "12px" }}>
                            {Object.entries(operationsData.version_currency.age_categories).map(([category, count]) => (
                              <div key={category} style={{ padding: "12px", background: "var(--sl-color-neutral-100)", borderRadius: "8px", textAlign: "center" }}>
                                <div style={{ fontSize: "24px", fontWeight: "bold", color: category.includes("EOL") ? "var(--sl-color-danger-600)" : "var(--sl-color-primary-600)" }}>
                                  {count}
                                </div>
                                <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginTop: "4px" }}>
                                  {category}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* By Platform */}
                        <h4 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "12px" }}>By Platform</h4>
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                          <thead>
                            <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Platform</th>
                              <th style={{ padding: "12px", textAlign: "right", fontWeight: "600", fontSize: "15px" }}>Total</th>
                              <th style={{ padding: "12px", textAlign: "right", fontWeight: "600", fontSize: "15px" }}>Current</th>
                              <th style={{ padding: "12px", textAlign: "right", fontWeight: "600", fontSize: "15px" }}>Outdated</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(operationsData.version_currency.by_platform).map(([platform, stats]) => (
                              <tr key={platform} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                                <td style={{ padding: "12px", fontSize: "15px" }}>{platform}</td>
                                <td style={{ padding: "12px", textAlign: "right", fontSize: "15px" }}>{stats.total}</td>
                                <td style={{ padding: "12px", textAlign: "right", fontSize: "15px", color: "var(--sl-color-success-600)" }}>
                                  {stats.current}
                                </td>
                                <td style={{ padding: "12px", textAlign: "right", fontSize: "15px", color: stats.outdated > 0 ? "var(--sl-color-warning-600)" : "var(--sl-color-neutral-600)" }}>
                                  {stats.outdated}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </sl-card>

                    {/* EOL Warnings */}
                    {operationsData.version_currency.eol_warnings.length > 0 && (
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)", marginBottom: "24px" }}>
                        <div slot="header" style={{ fontSize: "18px", fontWeight: "600", color: "var(--sl-color-danger-600)" }}>
                          ⚠️ EOL/Unsupported Sensor Warnings
                        </div>
                        <div style={{ padding: "16px" }}>
                          <sl-alert variant="danger" open style={{ marginBottom: "16px" }}>
                            <sl-icon slot="icon" name="exclamation-octagon-fill"></sl-icon>
                            <strong>{operationsData.version_currency.eol_warnings.length} hosts</strong> are running end-of-life sensor versions that may not be supported.
                          </sl-alert>
                          <table style={{ width: "100%", borderCollapse: "collapse" }}>
                            <thead>
                              <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                                <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Hostname</th>
                                <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Platform</th>
                                <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Version</th>
                                <th style={{ padding: "12px", textAlign: "right", fontWeight: "600", fontSize: "15px" }}>Age (months)</th>
                              </tr>
                            </thead>
                            <tbody>
                              {operationsData.version_currency.eol_warnings.slice(0, 20).map((warning, idx) => (
                                <tr key={idx} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                                  <td style={{ padding: "12px", fontSize: "15px" }}>{warning.hostname}</td>
                                  <td style={{ padding: "12px", fontSize: "15px" }}>{warning.platform}</td>
                                  <td style={{ padding: "12px", fontSize: "15px" }}>
                                    <sl-badge variant="danger">{warning.version}</sl-badge>
                                  </td>
                                  <td style={{ padding: "12px", textAlign: "right", fontSize: "15px", color: "var(--sl-color-danger-600)" }}>
                                    {warning.age_months}+
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {operationsData.version_currency.eol_warnings.length > 20 && (
                            <p style={{ marginTop: "12px", fontSize: "16px", color: "var(--sl-color-neutral-600)", textAlign: "center" }}>
                              Showing 20 of {operationsData.version_currency.eol_warnings.length} EOL hosts
                            </p>
                          )}
                        </div>
                      </sl-card>
                    )}

                    {/* Policy Assignments */}
                    <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                      <div slot="header" style={{ fontSize: "18px", fontWeight: "600", color: "var(--sl-color-neutral-900)" }}>
                        📋 Policy Assignment Distribution
                      </div>
                      <div style={{ padding: "16px" }}>
                        {operationsData.policy_assignments.unassigned > 0 && (
                          <sl-alert variant="warning" open style={{ marginBottom: "16px" }}>
                            <sl-icon slot="icon" name="exclamation-triangle-fill"></sl-icon>
                            <strong>{operationsData.policy_assignments.unassigned} hosts</strong> do not have prevention policies assigned.
                          </sl-alert>
                        )}
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                          <thead>
                            <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Policy Name</th>
                              <th style={{ padding: "12px", textAlign: "right", fontWeight: "600", fontSize: "15px" }}>Host Count</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(operationsData.policy_assignments.by_policy)
                              .sort(([, a], [, b]) => b.host_count - a.host_count)
                              .map(([policyName, stats]) => (
                                <tr key={policyName} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                                  <td style={{ padding: "12px", fontSize: "15px" }}>{policyName}</td>
                                  <td style={{ padding: "12px", textAlign: "right", fontSize: "15px" }}>
                                    <sl-badge variant="primary" pill>{stats.host_count}</sl-badge>
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    </sl-card>
                  </>
                )}
              </div>
            </sl-tab-panel>

            {/* Host Health Tab Panel */}
            <sl-tab-panel name="host-health">
              <div style={{ marginTop: "20px" }}>
                {hostHealthLoading && (
                  <div style={{ textAlign: "center", padding: "40px" }}>
                    <sl-spinner style={{ fontSize: "48px", "--track-width": "8px" }}></sl-spinner>
                    <p style={{ marginTop: "16px", color: "var(--sl-color-neutral-600)" }}>Loading host health data...</p>
                  </div>
                )}

                {hostHealthError && (
                  <sl-alert variant="danger" open>
                    <sl-icon slot="icon" name="exclamation-triangle-fill"></sl-icon>
                    <strong>Host Health Error:</strong> {hostHealthError}
                  </sl-alert>
                )}

                {hostHealthData && (
                  <>
                    {/* Overall Health Score Card */}
                    <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)", marginBottom: "24px" }}>
                      <div style={{ padding: "16px", textAlign: "center" }}>
                        <h3 style={{ fontSize: "18px", fontWeight: "600", marginBottom: "16px" }}>Overall Host Health</h3>
                        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "24px" }}>
                          <div>
                            <div style={{ fontSize: "48px", fontWeight: "bold", color: getScoreColor(hostHealthData.overall_health.score) }}>
                              {hostHealthData.overall_health.score}
                            </div>
                            <sl-badge variant={getStatusVariant(hostHealthData.overall_health.status)} pill style={{ fontSize: "16px" }}>
                              {hostHealthData.overall_health.status}
                            </sl-badge>
                          </div>
                          <div style={{ textAlign: "left" }}>
                            <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginBottom: "8px" }}>
                              Total Hosts: <strong>{hostHealthData.overall_health.total_hosts}</strong>
                            </div>
                            <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)" }}>
                              Total Issues: <strong style={{ color: hostHealthData.overall_health.total_issues > 0 ? "var(--sl-color-danger-600)" : "var(--sl-color-success-600)" }}>
                                {hostHealthData.overall_health.total_issues}
                              </strong>
                            </div>
                          </div>
                        </div>
                      </div>
                    </sl-card>

                    {/* Metric Cards */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "24px" }}>
                      {/* RFM Hosts Card */}
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "36px", fontWeight: "bold", color: hostHealthData.rfm_hosts.count > 0 ? "var(--sl-color-danger-600)" : "var(--sl-color-success-600)" }}>
                            {hostHealthData.rfm_hosts.count}
                          </div>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginTop: "8px" }}>
                            RFM Hosts
                          </div>
                          <sl-badge variant={hostHealthData.rfm_hosts.count > 0 ? "danger" : "success"} pill style={{ marginTop: "8px" }}>
                            {hostHealthData.rfm_hosts.severity}
                          </sl-badge>
                        </div>
                      </sl-card>

                      {/* Unmanaged Hosts Card */}
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "36px", fontWeight: "bold", color: hostHealthData.unmanaged_hosts.count > 0 ? "var(--sl-color-warning-600)" : "var(--sl-color-success-600)" }}>
                            {hostHealthData.unmanaged_hosts.count}
                          </div>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginTop: "8px" }}>
                            Unmanaged Hosts
                          </div>
                          <sl-badge variant={hostHealthData.unmanaged_hosts.count > 0 ? "warning" : "success"} pill style={{ marginTop: "8px" }}>
                            {hostHealthData.unmanaged_hosts.severity}
                          </sl-badge>
                        </div>
                      </sl-card>

                      {/* Stale Hosts Card */}
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "36px", fontWeight: "bold", color: hostHealthData.stale_hosts.count > 0 ? "var(--sl-color-warning-600)" : "var(--sl-color-success-600)" }}>
                            {hostHealthData.stale_hosts.count}
                          </div>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginTop: "8px" }}>
                            Stale Hosts ({hostHealthData.stale_hosts.threshold_days}+ days)
                          </div>
                          <sl-badge variant={hostHealthData.stale_hosts.count > 0 ? "warning" : "success"} pill style={{ marginTop: "8px" }}>
                            {hostHealthData.stale_hosts.severity}
                          </sl-badge>
                        </div>
                      </sl-card>

                      {/* Isolated Hosts Card */}
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "36px", fontWeight: "bold", color: hostHealthData.isolated_hosts.count > 0 ? "var(--sl-color-warning-600)" : "var(--sl-color-success-600)" }}>
                            {hostHealthData.isolated_hosts.count}
                          </div>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginTop: "8px" }}>
                            Isolated Hosts
                          </div>
                          <sl-badge variant={hostHealthData.isolated_hosts.count > 0 ? "warning" : "success"} pill style={{ marginTop: "8px" }}>
                            {hostHealthData.isolated_hosts.severity}
                          </sl-badge>
                        </div>
                      </sl-card>

                      {/* Policy Gaps Card */}
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)" }}>
                        <div style={{ padding: "16px" }}>
                          <div style={{ fontSize: "36px", fontWeight: "bold", color: hostHealthData.policy_gaps.count > 0 ? "var(--sl-color-danger-600)" : "var(--sl-color-success-600)" }}>
                            {hostHealthData.policy_gaps.count}
                          </div>
                          <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-600)", marginTop: "8px" }}>
                            Policy Gaps
                          </div>
                          <sl-badge variant={hostHealthData.policy_gaps.count > 0 ? "danger" : "success"} pill style={{ marginTop: "8px" }}>
                            {hostHealthData.policy_gaps.severity}
                          </sl-badge>
                        </div>
                      </sl-card>
                    </div>

                    {/* Recommendations Section */}
                    {hostHealthData.recommendations && hostHealthData.recommendations.length > 0 && (
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)", marginBottom: "24px" }}>
                        <div slot="header" style={{ fontSize: "18px", fontWeight: "600", color: "var(--sl-color-neutral-900)" }}>
                          🎯 Priority Recommendations
                        </div>
                        <div style={{ padding: "16px" }}>
                          {hostHealthData.recommendations.map((rec, idx) => (
                            <sl-alert
                              key={idx}
                              variant={rec.severity === "critical" ? "danger" : rec.severity === "high" ? "warning" : rec.severity === "success" ? "success" : "primary"}
                              open
                              style={{ marginBottom: idx < hostHealthData.recommendations.length - 1 ? "12px" : "0" }}
                            >
                              <sl-icon slot="icon" name={rec.severity === "success" ? "check-circle-fill" : "exclamation-triangle-fill"}></sl-icon>
                              <strong>Priority {rec.priority}: {rec.issue}</strong><br/>
                              {rec.recommendation}
                              {rec.affected_count > 0 && (
                                <div style={{ marginTop: "8px", fontSize: "16px", color: "var(--sl-color-neutral-600)" }}>
                                  Affected hosts: {rec.affected_count}
                                </div>
                              )}
                            </sl-alert>
                          ))}
                        </div>
                      </sl-card>
                    )}

                    {/* RFM Hosts Details */}
                    {hostHealthData.rfm_hosts.count > 0 && (
                      <sl-details summary={`🔴 RFM Hosts (${hostHealthData.rfm_hosts.count})`} style={{ marginBottom: "16px" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "8px" }}>
                          <thead>
                            <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Hostname</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Platform</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Last Seen</th>
                              <th style={{ padding: "12px", textAlign: "center", fontWeight: "600", fontSize: "15px" }}>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {hostHealthData.rfm_hosts.hosts.slice(0, 50).map((host, idx) => (
                              <tr key={idx} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                                <td style={{ padding: "12px" }}>{host.hostname}</td>
                                <td style={{ padding: "12px" }}>
                                  <sl-badge variant="neutral">{host.platform}</sl-badge>
                                </td>
                                <td style={{ padding: "12px", fontSize: "16px", color: "var(--sl-color-neutral-600)" }}>{host.last_seen}</td>
                                <td style={{ padding: "12px", textAlign: "center" }}>
                                  <sl-badge variant="danger">RFM</sl-badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </sl-details>
                    )}

                    {/* Unmanaged Hosts Details */}
                    {hostHealthData.unmanaged_hosts.count > 0 && (
                      <sl-details summary={`🟡 Unmanaged Hosts (${hostHealthData.unmanaged_hosts.count})`} style={{ marginBottom: "16px" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "8px" }}>
                          <thead>
                            <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Hostname</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Platform</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Local IP</th>
                              <th style={{ padding: "12px", textAlign: "center", fontWeight: "600", fontSize: "15px" }}>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {hostHealthData.unmanaged_hosts.hosts.slice(0, 50).map((host, idx) => (
                              <tr key={idx} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                                <td style={{ padding: "12px" }}>{host.hostname}</td>
                                <td style={{ padding: "12px" }}>
                                  <sl-badge variant="neutral">{host.platform}</sl-badge>
                                </td>
                                <td style={{ padding: "12px", fontSize: "16px", color: "var(--sl-color-neutral-600)" }}>{host.local_ip}</td>
                                <td style={{ padding: "12px", textAlign: "center" }}>
                                  <sl-badge variant="warning">Unmanaged</sl-badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </sl-details>
                    )}

                    {/* Stale Hosts Details */}
                    {hostHealthData.stale_hosts.count > 0 && (
                      <sl-details summary={`⏰ Stale Hosts (${hostHealthData.stale_hosts.count})`} style={{ marginBottom: "16px" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "8px" }}>
                          <thead>
                            <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Hostname</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Platform</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Last Seen</th>
                              <th style={{ padding: "12px", textAlign: "center", fontWeight: "600", fontSize: "15px" }}>Days Offline</th>
                            </tr>
                          </thead>
                          <tbody>
                            {hostHealthData.stale_hosts.hosts.slice(0, 50).map((host, idx) => (
                              <tr key={idx} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                                <td style={{ padding: "12px" }}>{host.hostname}</td>
                                <td style={{ padding: "12px" }}>
                                  <sl-badge variant="neutral">{host.platform}</sl-badge>
                                </td>
                                <td style={{ padding: "12px", fontSize: "16px", color: "var(--sl-color-neutral-600)" }}>{host.last_seen}</td>
                                <td style={{ padding: "12px", textAlign: "center" }}>
                                  <sl-badge variant={host.days_offline > 30 ? "danger" : "warning"}>{host.days_offline} days</sl-badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </sl-details>
                    )}

                    {/* Isolated Hosts Details */}
                    {hostHealthData.isolated_hosts.count > 0 && (
                      <sl-details summary={`🚨 Isolated Hosts (${hostHealthData.isolated_hosts.count})`} style={{ marginBottom: "16px" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "8px" }}>
                          <thead>
                            <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Hostname</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Platform</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Last Seen</th>
                              <th style={{ padding: "12px", textAlign: "center", fontWeight: "600", fontSize: "15px" }}>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {hostHealthData.isolated_hosts.hosts.slice(0, 50).map((host, idx) => (
                              <tr key={idx} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                                <td style={{ padding: "12px" }}>{host.hostname}</td>
                                <td style={{ padding: "12px" }}>
                                  <sl-badge variant="neutral">{host.platform}</sl-badge>
                                </td>
                                <td style={{ padding: "12px", fontSize: "16px", color: "var(--sl-color-neutral-600)" }}>{host.last_seen}</td>
                                <td style={{ padding: "12px", textAlign: "center" }}>
                                  <sl-badge variant="warning">Contained</sl-badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </sl-details>
                    )}

                    {/* Policy Gaps Details */}
                    {hostHealthData.policy_gaps.count > 0 && (
                      <sl-details summary={`⚠️ Policy Gaps (${hostHealthData.policy_gaps.count})`} style={{ marginBottom: "16px" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "8px" }}>
                          <thead>
                            <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Hostname</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Platform</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Last Seen</th>
                              <th style={{ padding: "12px", textAlign: "center", fontWeight: "600", fontSize: "15px" }}>Issue</th>
                            </tr>
                          </thead>
                          <tbody>
                            {hostHealthData.policy_gaps.hosts.slice(0, 50).map((host, idx) => (
                              <tr key={idx} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                                <td style={{ padding: "12px" }}>{host.hostname}</td>
                                <td style={{ padding: "12px" }}>
                                  <sl-badge variant="neutral">{host.platform}</sl-badge>
                                </td>
                                <td style={{ padding: "12px", fontSize: "16px", color: "var(--sl-color-neutral-600)" }}>{host.last_seen}</td>
                                <td style={{ padding: "12px", textAlign: "center" }}>
                                  <sl-badge variant="danger">No Policy</sl-badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </sl-details>
                    )}

                    {/* Host Groups Health */}
                    {hostHealthData.host_groups && hostHealthData.host_groups.groups && hostHealthData.host_groups.groups.length > 0 && (
                      <sl-card style={{ "--border-radius": "var(--sl-border-radius-large)", boxShadow: "var(--sl-shadow-large)", marginTop: "24px" }}>
                        <div slot="header" style={{ fontSize: "18px", fontWeight: "600", color: "var(--sl-color-neutral-900)" }}>
                          📊 Host Groups Health
                        </div>
                        <div style={{ padding: "16px" }}>
                          <table style={{ width: "100%", borderCollapse: "collapse" }}>
                            <thead>
                              <tr style={{ background: "var(--sl-color-neutral-100)", borderBottom: "2px solid var(--sl-color-neutral-200)" }}>
                                <th style={{ padding: "12px", textAlign: "left", fontWeight: "600", fontSize: "15px" }}>Group Name</th>
                                <th style={{ padding: "12px", textAlign: "center", fontWeight: "600", fontSize: "15px" }}>Total Hosts</th>
                                <th style={{ padding: "12px", textAlign: "center", fontWeight: "600", fontSize: "15px" }}>Health Score</th>
                                <th style={{ padding: "12px", textAlign: "center", fontWeight: "600", fontSize: "15px" }}>RFM</th>
                                <th style={{ padding: "12px", textAlign: "center", fontWeight: "600", fontSize: "15px" }}>Stale</th>
                                <th style={{ padding: "12px", textAlign: "center", fontWeight: "600", fontSize: "15px" }}>Policy Gaps</th>
                              </tr>
                            </thead>
                            <tbody>
                              {hostHealthData.host_groups.groups.slice(0, 20).map((group, idx) => (
                                <tr key={idx} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                                  <td style={{ padding: "12px", fontWeight: "600" }}>{group.group_name}</td>
                                  <td style={{ padding: "12px", textAlign: "center" }}>{group.total_hosts}</td>
                                  <td style={{ padding: "12px", textAlign: "center" }}>
                                    <sl-badge variant={group.health_score >= 90 ? "success" : group.health_score >= 70 ? "primary" : group.health_score >= 50 ? "warning" : "danger"}>
                                      {group.health_score}
                                    </sl-badge>
                                  </td>
                                  <td style={{ padding: "12px", textAlign: "center" }}>
                                    {group.rfm_count > 0 ? (
                                      <span style={{ color: "var(--sl-color-danger-600)", fontWeight: "600" }}>{group.rfm_count}</span>
                                    ) : (
                                      <span style={{ color: "var(--sl-color-success-600)" }}>✓</span>
                                    )}
                                  </td>
                                  <td style={{ padding: "12px", textAlign: "center" }}>
                                    {group.stale_count > 0 ? (
                                      <span style={{ color: "var(--sl-color-warning-600)", fontWeight: "600" }}>{group.stale_count}</span>
                                    ) : (
                                      <span style={{ color: "var(--sl-color-success-600)" }}>✓</span>
                                    )}
                                  </td>
                                  <td style={{ padding: "12px", textAlign: "center" }}>
                                    {group.policy_gaps > 0 ? (
                                      <span style={{ color: "var(--sl-color-danger-600)", fontWeight: "600" }}>{group.policy_gaps}</span>
                                    ) : (
                                      <span style={{ color: "var(--sl-color-success-600)" }}>✓</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </sl-card>
                    )}
                  </>
                )}
              </div>
            </sl-tab-panel>
          </sl-tab-group>
        </>
      )}

      {showPolicyDialog && (
      <sl-dialog
        open
        onSlAfterHide={() => { setShowPolicyDialog(false); setApplyResult(null); }}
        label={selectedPolicy ? `${selectedPolicy.name} - Configuration Details` : "Policy Details"}
        style={{ "--width": "820px" }}
      >
        <div style={{ maxHeight: "62vh", overflowY: "auto", paddingRight: "4px" }}>
        {selectedPolicy && selectedPolicy.analysis && (
          <div>
            {/* Overview */}
            <div style={{ marginBottom: "20px", padding: "16px", background: "var(--sl-color-neutral-100)", borderRadius: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginBottom: "4px", fontWeight: "500" }}>Platform</div>
                  <sl-badge variant="neutral" style={{ marginTop: "4px" }}>{selectedPolicy.platform}</sl-badge>
                </div>
                <div>
                  <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginBottom: "4px", fontWeight: "500" }}>Status</div>
                  <sl-badge variant={selectedPolicy.enabled ? "success" : "neutral"} pill style={{ marginTop: "4px" }}>
                    {selectedPolicy.enabled ? "✓ Enabled" : "Disabled"}
                  </sl-badge>
                </div>
                <div>
                  <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", marginBottom: "4px", fontWeight: "500" }}>Compliance</div>
                  <div style={{ fontSize: "24px", fontWeight: "bold", marginTop: "4px", color: selectedPolicy.analysis.compliance_percentage >= 75 ? "var(--sl-color-success-600)" : "var(--sl-color-danger-600)" }}>
                    {selectedPolicy.analysis.compliance_percentage || 0}%
                  </div>
                </div>
              </div>
            </div>

            {/* Issues */}
            {selectedPolicy.analysis.issues && selectedPolicy.analysis.issues.length > 0 && (
              <sl-alert variant="warning" open style={{ marginBottom: "20px" }}>
                <strong>⚠️ Issues Found ({selectedPolicy.analysis.issues.length})</strong>
                <ul style={{ marginTop: "8px", marginBottom: "0", paddingLeft: "20px" }}>
                  {selectedPolicy.analysis.issues.map((issue, idx) => (
                    <li key={idx} style={{ marginBottom: "4px" }}>{issue}</li>
                  ))}
                </ul>
              </sl-alert>
            )}

            {/* Recommendations */}
            {selectedPolicy.analysis.recommendations && selectedPolicy.analysis.recommendations.length > 0 && (
              <sl-alert variant="primary" open style={{ marginBottom: "20px" }}>
                <strong>💡 Recommendations ({selectedPolicy.analysis.recommendations.length})</strong>
                <ul style={{ marginTop: "8px", marginBottom: "0", paddingLeft: "20px" }}>
                  {selectedPolicy.analysis.recommendations.map((rec, idx) => (
                    <li key={idx} style={{ marginBottom: "4px" }}>{rec}</li>
                  ))}
                </ul>
              </sl-alert>
            )}

            {/* Detailed Configuration */}
            {selectedPolicy.analysis.detailed_config && Object.keys(selectedPolicy.analysis.detailed_config).length > 0 && (
              <div>
                <h4 style={{ marginBottom: "12px", color: "var(--sl-color-neutral-900)" }}>📋 Detailed Configuration</h4>
                {Object.entries(selectedPolicy.analysis.detailed_config).map(([category, settings]) => (
                  <sl-details key={category} summary={category.replace(/_/g, ' ').toUpperCase()} style={{ marginBottom: "12px" }}>
                    <div style={{ padding: "8px" }}>
                      <table style={{ width: "100%", fontSize: "16px" }}>
                        <thead>
                          <tr style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                            <th style={{ padding: "8px", textAlign: "left", color: "var(--sl-color-neutral-700)" }}>Setting</th>
                            <th style={{ padding: "8px", textAlign: "center", color: "var(--sl-color-neutral-700)" }}>Current</th>
                            <th style={{ padding: "8px", textAlign: "center", color: "var(--sl-color-neutral-700)" }}>Expected</th>
                            <th style={{ padding: "8px", textAlign: "center", color: "var(--sl-color-neutral-700)" }}>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(settings).map(([setting, comparison]) => (
                            <tr key={setting} style={{ borderBottom: "1px solid var(--sl-color-neutral-200)" }}>
                              <td style={{ padding: "8px", color: "var(--sl-color-neutral-900)" }}>{setting.replace(/_/g, ' ')}</td>
                              <td style={{ padding: "8px", textAlign: "center" }}>
                                <sl-badge variant="neutral">{comparison.actual}</sl-badge>
                              </td>
                              <td style={{ padding: "8px", textAlign: "center" }}>
                                <sl-badge variant="primary">{comparison.expected}</sl-badge>
                              </td>
                              <td style={{ padding: "8px", textAlign: "center" }}>
                                {comparison.compliant ? (
                                  <span style={{ color: "var(--sl-color-success-600)" }}>✓</span>
                                ) : (
                                  <span style={{ color: "var(--sl-color-danger-600)" }}>✗</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </sl-details>
                ))}
              </div>
            )}

            {/* Summary Stats */}
            <div style={{ marginTop: "20px", padding: "16px", background: "var(--sl-color-neutral-100)", borderRadius: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-around", textAlign: "center" }}>
                <div>
                  <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", fontWeight: "500" }}>Total Checks</div>
                  <div style={{ fontSize: "20px", fontWeight: "bold", color: "var(--sl-color-neutral-900)" }}>{selectedPolicy.analysis.total_checks || 0}</div>
                </div>
                <div>
                  <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", fontWeight: "500" }}>Compliant</div>
                  <div style={{ fontSize: "20px", fontWeight: "bold", color: "var(--sl-color-success-600)" }}>{selectedPolicy.analysis.compliant_checks || 0}</div>
                </div>
                <div>
                  <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", fontWeight: "500" }}>Non-Compliant</div>
                  <div style={{ fontSize: "20px", fontWeight: "bold", color: "var(--sl-color-danger-600)" }}>
                    {(selectedPolicy.analysis.total_checks || 0) - (selectedPolicy.analysis.compliant_checks || 0)}
                  </div>
                </div>
                {selectedPolicy.analysis.coverage_percentage !== undefined && (
                  <div>
                    <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)", fontWeight: "500" }}>Coverage</div>
                    <div style={{ fontSize: "20px", fontWeight: "bold", color: selectedPolicy.analysis.coverage_percentage >= 90 ? "var(--sl-color-success-600)" : selectedPolicy.analysis.coverage_percentage >= 70 ? "var(--sl-color-warning-600)" : "var(--sl-color-danger-600)" }}>
                      {selectedPolicy.analysis.coverage_percentage}%
                    </div>
                    <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-500)" }}>
                      {selectedPolicy.analysis.sensor_count || 0} sensors
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* What will change — non-compliant settings list */}
        {selectedPolicy && selectedPolicy.analysis && selectedPolicy.analysis.non_compliant_settings && selectedPolicy.analysis.non_compliant_settings.length > 0 && !applyResult?.success && (
          <div style={{ marginTop: "20px" }}>
            <h4 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "10px", color: "var(--sl-color-neutral-900)" }}>
              What will change ({selectedPolicy.analysis.non_compliant_settings.length} settings not meeting best practices)
            </h4>
            <div style={{ border: "1px solid var(--sl-color-neutral-200)", borderRadius: "8px", overflow: "hidden" }}>
              {selectedPolicy.analysis.non_compliant_settings.map((s, idx) => (
                <div key={idx} style={{
                  display: "flex", alignItems: "center", gap: "12px", padding: "10px 14px",
                  borderBottom: idx < selectedPolicy.analysis.non_compliant_settings.length - 1 ? "1px solid var(--sl-color-neutral-200)" : "none",
                  background: idx % 2 === 0 ? "var(--sl-color-neutral-100)" : "transparent"
                }}>
                  <sl-badge variant={s.severity === "CRITICAL" ? "danger" : s.severity === "HIGH" ? "warning" : "neutral"} style={{ flexShrink: 0, fontSize: "15px" }}>
                    {s.severity}
                  </sl-badge>
                  <div style={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span
                        title={s.setting_id}
                        style={{ fontSize: "16px", fontWeight: "600", color: "var(--sl-color-neutral-900)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "220px" }}
                      >{s.setting_id}</span>
                      <span
                        onClick={() => (window.top || window).open(PREVENTION_DOCS[s.setting_id] || PREVENTION_DOCS.default, '_blank')}
                        style={{ fontSize: "15px", color: "var(--sl-color-primary-600)", cursor: "pointer", flexShrink: 0 }}
                      >
                        Docs ↗
                      </span>
                    </div>
                    <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-500)", marginTop: "2px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.description}</div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "4px", flexShrink: 0, fontSize: "15px" }}>
                    <sl-badge variant="danger" style={{ fontSize: "15px", maxWidth: "130px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {typeof s.current === "object" ? JSON.stringify(s.current) : String(s.current)}
                    </sl-badge>
                    <sl-badge variant="success" style={{ fontSize: "15px", maxWidth: "130px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.recommended}</sl-badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Apply result feedback */}
        {applyResult && (
          <sl-alert variant={applyResult.success ? "success" : "danger"} open style={{ marginTop: "16px" }}>
            {applyResult.success ? (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
                <span>Applied {applyResult.changes_made} changes. Compliance: {applyResult.compliance_before}% → {applyResult.compliance_after}%</span>
                <sl-button size="small" variant="success" outline onClick={() => { setShowPolicyDialog(false); setApplyResult(null); fetchHealthCheck(); }}>
                  Refresh Dashboard
                </sl-button>
              </div>
            ) : `Failed: ${applyResult.message}`}
          </sl-alert>
        )}

        {/* Sticky action bar — always visible at bottom of scroll area */}
        <div style={{
          position: "sticky", bottom: 0,
          background: "var(--sl-panel-background-color, var(--sl-color-neutral-0))",
          borderTop: "1px solid var(--sl-color-neutral-200)",
          padding: "12px 0 4px",
          display: "flex", gap: "8px", justifyContent: "flex-end",
          marginTop: "16px"
        }}>
          {selectedPolicy && selectedPolicy.analysis && selectedPolicy.analysis.compliance_percentage < 100 && !applyResult?.success && (
            <sl-button
              variant="success"
              onClick={() => applyBestPractices(selectedPolicy.id, selectedPolicy.name, false)}
              loading={applyingBestPractices[selectedPolicy?.id]}
              disabled={applyingBestPractices[selectedPolicy?.id]}
            >
              Apply Best Practices
            </sl-button>
          )}
          <sl-button variant="default" onClick={() => setShowPolicyDialog(false)}>Close</sl-button>
        </div>
        </div>{/* end scrollable wrapper */}
      </sl-dialog>
      )}

      {showSnapshotDialog && (
      <sl-dialog
        open
        onSlAfterHide={() => setShowSnapshotDialog(false)}
        label="Select Snapshots for Drift Detection"
        style={{ "--width": "600px" }}
      >
        <div>
          <p style={{ marginBottom: "16px", color: "var(--sl-color-neutral-700)" }}>
            Select a baseline snapshot and a current snapshot to compare for configuration drift.
          </p>

          {snapshots.length >= 1 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {snapshots.length === 1 && (
                <sl-alert variant="primary" open>
                  <sl-icon slot="icon" name="info-circle"></sl-icon>
                  You have 1 snapshot. Create a second one after making policy changes to detect drift. For now you can compare this snapshot against itself — it will show 0 drift.
                </sl-alert>
              )}
              <div>
                <label style={{ fontWeight: "600", marginBottom: "8px", display: "block", color: "var(--sl-color-neutral-900)" }}>Baseline Snapshot (older)</label>
                <select
                  id="baseline-snapshot"
                  style={{
                    width: "100%", padding: "8px", borderRadius: "4px",
                    border: "1px solid var(--sl-color-neutral-300)",
                    background: "var(--sl-color-neutral-0)",
                    color: "var(--sl-color-neutral-900)"
                  }}
                >
                  {snapshots.map((snap) => (
                    <option key={snap.snapshot_id} value={snap.snapshot_id}>
                      {new Date(snap.timestamp).toLocaleString()} — {snap.snapshot_type} ({snap.total_policies} policies)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontWeight: "600", marginBottom: "8px", display: "block", color: "var(--sl-color-neutral-900)" }}>Current Snapshot (newer)</label>
                <select
                  id="current-snapshot"
                  style={{
                    width: "100%", padding: "8px", borderRadius: "4px",
                    border: "1px solid var(--sl-color-neutral-300)",
                    background: "var(--sl-color-neutral-0)",
                    color: "var(--sl-color-neutral-900)"
                  }}
                >
                  {snapshots.map((snap, idx) => (
                    <option key={snap.snapshot_id} value={snap.snapshot_id} selected={idx === 0}>
                      {new Date(snap.timestamp).toLocaleString()} — {snap.snapshot_type} ({snap.total_policies} policies)
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <sl-alert variant="warning" open>
              <sl-icon slot="icon" name="exclamation-triangle"></sl-icon>
              <strong>No snapshots yet.</strong> Create a snapshot first using the "Create Snapshot" button.
            </sl-alert>
          )}
        </div>

        <div slot="footer" style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
          <sl-button variant="default" onClick={() => setShowSnapshotDialog(false)}>
            Cancel
          </sl-button>
          <sl-button
            variant="primary"
            onClick={() => {
              const baselineId = document.getElementById('baseline-snapshot')?.value;
              const currentId = document.getElementById('current-snapshot')?.value;
              if (baselineId && currentId) {
                detectDrift(baselineId, currentId);
                setShowSnapshotDialog(false);
              }
            }}
            disabled={snapshots.length < 1}
            loading={driftLoading}
          >
            Detect Drift
          </sl-button>
        </div>
      </sl-dialog>
      )}

      {showDriftDialog && (
      <sl-dialog
        open
        onSlAfterHide={() => setShowDriftDialog(false)}
        label="Drift Detection Results"
        style={{ "--width": "900px" }}
      >
        {driftData && (
          <div>
            {/* Summary */}
            <div style={{ marginBottom: "20px", padding: "16px", background: "var(--sl-color-neutral-100)", borderRadius: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <h4 style={{ margin: 0 }}>Summary</h4>
                <sl-badge variant={driftData.drift_detected ? "warning" : "success"} pill>
                  {driftData.drift_detected ? `${driftData.total_drift_events} Changes Detected` : "No Drift"}
                </sl-badge>
              </div>

              {driftData.summary && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "24px", fontWeight: "bold", color: "var(--sl-color-danger-600)" }}>
                      {driftData.summary.critical || 0}
                    </div>
                    <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)" }}>Critical</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "24px", fontWeight: "bold", color: "var(--sl-color-warning-600)" }}>
                      {driftData.summary.high || 0}
                    </div>
                    <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)" }}>High</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "24px", fontWeight: "bold", color: "var(--sl-color-primary-600)" }}>
                      {driftData.summary.medium || 0}
                    </div>
                    <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)" }}>Medium</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "24px", fontWeight: "bold", color: "var(--sl-color-neutral-600)" }}>
                      {driftData.summary.low || 0}
                    </div>
                    <div style={{ fontSize: "16px", color: "var(--sl-color-neutral-600)" }}>Low</div>
                  </div>
                </div>
              )}
            </div>

            {/* Drift Events */}
            {driftData.drift_events && driftData.drift_events.length > 0 && (
              <div>
                <h4 style={{ marginBottom: "12px" }}>Detected Changes</h4>
                <div style={{ maxHeight: "400px", overflow: "auto" }}>
                  {driftData.drift_events.map((event, idx) => (
                    <sl-details key={idx} summary={`${event.policy_name} - ${event.drift_type}`} style={{ marginBottom: "8px" }}>
                      <div style={{ padding: "12px" }}>
                        <div style={{ marginBottom: "8px" }}>
                          <sl-badge
                            variant={
                              event.risk_level === "CRITICAL" ? "danger" :
                              event.risk_level === "HIGH" ? "warning" :
                              event.risk_level === "MEDIUM" ? "primary" : "neutral"
                            }
                          >
                            {event.risk_level}
                          </sl-badge>
                          <sl-badge variant="neutral" style={{ marginLeft: "8px" }}>
                            {event.policy_type}
                          </sl-badge>
                        </div>

                        {/* Show detailed changes for prevention policies */}
                        {event.changes && event.changes.prevention_settings && Array.isArray(event.changes.prevention_settings) && (
                          <div style={{ marginTop: "12px" }}>
                            <strong>Settings Changed ({event.changes.prevention_settings.length}):</strong>
                            <table style={{ width: "100%", marginTop: "8px", fontSize: "16px", borderCollapse: "collapse" }}>
                              <thead>
                                <tr style={{ background: "var(--sl-color-neutral-100)" }}>
                                  <th style={{ padding: "6px", textAlign: "left", border: "1px solid var(--sl-color-neutral-200)" }}>Category</th>
                                  <th style={{ padding: "6px", textAlign: "left", border: "1px solid var(--sl-color-neutral-200)" }}>Setting</th>
                                  <th style={{ padding: "6px", textAlign: "left", border: "1px solid var(--sl-color-neutral-200)" }}>Old Value</th>
                                  <th style={{ padding: "6px", textAlign: "left", border: "1px solid var(--sl-color-neutral-200)" }}>New Value</th>
                                </tr>
                              </thead>
                              <tbody>
                                {event.changes.prevention_settings.slice(0, 20).map((change, cidx) => (
                                  <tr key={cidx}>
                                    <td style={{ padding: "6px", border: "1px solid var(--sl-color-neutral-200)" }}>{change.category}</td>
                                    <td style={{ padding: "6px", border: "1px solid var(--sl-color-neutral-200)" }}>{change.setting}</td>
                                    <td style={{ padding: "6px", border: "1px solid var(--sl-color-neutral-200)", color: "var(--sl-color-danger-600)" }}>
                                      {String(change.old_value)}
                                    </td>
                                    <td style={{ padding: "6px", border: "1px solid var(--sl-color-neutral-200)", color: "var(--sl-color-success-600)" }}>
                                      {String(change.new_value)}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            {event.changes.prevention_settings.length > 20 && (
                              <div style={{ fontSize: "15px", color: "var(--sl-color-neutral-500)", marginTop: "4px" }}>
                                Showing 20 of {event.changes.prevention_settings.length} changes
                              </div>
                            )}
                          </div>
                        )}

                        {event.remediation_available && (
                          <div style={{ marginTop: "12px", padding: "8px", background: "var(--sl-color-primary-50)", borderRadius: "4px" }}>
                            <strong style={{ fontSize: "16px" }}>Remediation:</strong> {event.remediation_action}
                          </div>
                        )}
                      </div>
                    </sl-details>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <sl-button slot="footer" variant="primary" onClick={() => setShowDriftDialog(false)}>
          Close
        </sl-button>
      </sl-dialog>
      )}
    </div>
  );
}

export { Home };
