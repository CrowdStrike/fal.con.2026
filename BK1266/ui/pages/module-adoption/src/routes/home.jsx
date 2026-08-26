import React, { useContext, useState, useEffect } from "react";
import { FalconApiContext } from "../contexts/falcon-api-context";
import { setBasePath } from '@shoelace-style/shoelace/dist/utilities/base-path.js';
import "@shoelace-style/shoelace/dist/components/card/card.js";
import "@shoelace-style/shoelace/dist/components/button/button.js";
import "@shoelace-style/shoelace/dist/components/spinner/spinner.js";
import "@shoelace-style/shoelace/dist/components/badge/badge.js";
import "@shoelace-style/shoelace/dist/components/alert/alert.js";
import "@shoelace-style/shoelace/dist/components/icon/icon.js";
import "@shoelace-style/shoelace/dist/components/progress-ring/progress-ring.js";
import "@shoelace-style/shoelace/dist/components/progress-bar/progress-bar.js";

// Set Shoelace to use CDN for icons
setBasePath('https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.19.1/cdn/');

function Home() {
  const { falcon } = useContext(FalconApiContext);
  const [adoptionData, setAdoptionData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAdoptionData = async () => {
    setLoading(true);
    setError(null);
    try {
      const adoptionFn = falcon.cloudFunction({ name: 'module-adoption-checker' });
      const response = await adoptionFn.path('/api/adoption/check').get();

      console.log('Adoption Check Response:', JSON.stringify(response, null, 2));

      if (response.status_code !== 200) {
        const errorDetails = JSON.stringify(response.errors || response, null, 2);
        console.error('Function error details:', errorDetails);
        throw new Error(`Function call failed (${response.status_code}): ${errorDetails}`);
      }

      if (response && response.body) {
        setAdoptionData(response.body);
      } else {
        setError("No data returned from adoption check");
      }
    } catch (err) {
      console.error('Adoption check error:', err);
      const errorMessages = err.errors?.map(e => e.message || JSON.stringify(e)).join(', ');
      setError(`Error: ${errorMessages || err.message || "An error occurred"}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdoptionData();
  }, []);

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

  const getScoreColor = (score) => {
    if (score >= 80) return "var(--sl-color-success-600)";
    if (score >= 60) return "var(--sl-color-primary-600)";
    if (score >= 30) return "var(--sl-color-warning-600)";
    return "var(--sl-color-danger-600)";
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
      {/* Header */}
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ fontSize: "32px", fontWeight: "bold", marginBottom: "8px", color: "var(--sl-color-neutral-900)" }}>
          📊 Module Adoption Scorecard
        </h1>
        <p style={{ color: "var(--sl-color-neutral-600)", fontSize: "16px" }}>
          Are you getting full value from your CrowdStrike investment?
        </p>
      </div>

      {/* Action Bar */}
      <div style={{ marginBottom: "24px", display: "flex", gap: "12px", alignItems: "center" }}>
        <sl-button variant="primary" onClick={fetchAdoptionData} disabled={loading}>
          {loading ? (
            <>
              <sl-spinner slot="prefix"></sl-spinner>
              Checking...
            </>
          ) : (
            <>
              <sl-icon slot="prefix" name="arrow-clockwise"></sl-icon>
              Refresh Adoption Data
            </>
          )}
        </sl-button>
        {adoptionData && (
          <span style={{ fontSize: "13px", color: "var(--sl-color-neutral-600)" }}>
            Last checked: {new Date(adoptionData.scan_timestamp).toLocaleString()} ({adoptionData.scan_duration_ms}ms)
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
      {loading && !adoptionData && (
        <div style={{ textAlign: "center", padding: "60px" }}>
          <sl-spinner style={{ fontSize: "48px" }}></sl-spinner>
          <p style={{ marginTop: "16px", color: "var(--sl-color-neutral-600)" }}>
            Checking module adoption across your Falcon environment...
          </p>
        </div>
      )}

      {/* Adoption Dashboard */}
      {adoptionData && (
        <>
          {/* Summary Stats */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px", marginBottom: "32px" }}>
            {/* Overall Score */}
            <sl-card style={{
              "--border-radius": "var(--sl-border-radius-large)",
              boxShadow: "var(--sl-shadow-large)"
            }}>
              <div style={{ textAlign: "center", padding: "20px" }}>
                <div style={{ fontSize: "13px", fontWeight: "500", marginBottom: "16px", color: "var(--sl-color-neutral-600)" }}>
                  Overall Adoption Score
                </div>
                <sl-progress-ring
                  value={adoptionData.overall_score}
                  style={{
                    "--size": "120px",
                    "--track-width": "10px",
                    "--indicator-color": getScoreColor(adoptionData.overall_score),
                    "--track-color": "var(--sl-color-neutral-200)",
                    fontSize: "32px",
                    fontWeight: "bold",
                    color: "var(--sl-color-neutral-900)"
                  }}
                >
                  {Math.round(adoptionData.overall_score)}
                </sl-progress-ring>
                <div style={{ marginTop: "16px" }}>
                  <sl-badge variant={getAdoptionVariant(adoptionData.overall_level)} pill style={{ fontSize: "13px", padding: "4px 12px" }}>
                    {adoptionData.overall_level}
                  </sl-badge>
                </div>
              </div>
            </sl-card>

            {/* Modules Licensed */}
            <sl-card style={{
              "--border-radius": "var(--sl-border-radius-large)",
              boxShadow: "var(--sl-shadow-large)"
            }}>
              <div style={{ padding: "20px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: "13px", color: "var(--sl-color-neutral-600)", marginBottom: "8px", fontWeight: "500" }}>
                      Modules Licensed
                    </div>
                    <div style={{ fontSize: "36px", fontWeight: "bold", color: "var(--sl-color-neutral-900)" }}>
                      {adoptionData.licensed_module_count}
                    </div>
                    <div style={{ fontSize: "13px", color: "var(--sl-color-neutral-600)", marginTop: "6px", fontWeight: "500" }}>
                      of {adoptionData.total_modules_checked} checked
                    </div>
                  </div>
                  <div style={{ fontSize: "48px", opacity: 0.15 }}>📦</div>
                </div>
              </div>
            </sl-card>

            {/* Fully Adopted */}
            <sl-card style={{
              "--border-radius": "var(--sl-border-radius-large)",
              boxShadow: "var(--sl-shadow-large)"
            }}>
              <div style={{ padding: "20px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: "13px", color: "var(--sl-color-neutral-600)", marginBottom: "8px", fontWeight: "500" }}>
                      Fully Adopted
                    </div>
                    <div style={{ fontSize: "36px", fontWeight: "bold", color: "var(--sl-color-success-600)" }}>
                      {adoptionData.modules.filter(m => m.adoption_score >= 80).length}
                    </div>
                    <div style={{ fontSize: "13px", color: "var(--sl-color-neutral-600)", marginTop: "6px", fontWeight: "500" }}>
                      Score ≥ 80
                    </div>
                  </div>
                  <div style={{ fontSize: "48px", opacity: 0.15 }}>✅</div>
                </div>
              </div>
            </sl-card>

            {/* Needs Attention */}
            <sl-card style={{
              "--border-radius": "var(--sl-border-radius-large)",
              boxShadow: "var(--sl-shadow-large)"
            }}>
              <div style={{ padding: "20px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: "13px", color: "var(--sl-color-neutral-600)", marginBottom: "8px", fontWeight: "500" }}>
                      Needs Attention
                    </div>
                    <div style={{ fontSize: "36px", fontWeight: "bold", color: "var(--sl-color-warning-600)" }}>
                      {adoptionData.modules.filter(m => m.licensed && m.adoption_score < 50).length}
                    </div>
                    <div style={{ fontSize: "13px", color: "var(--sl-color-neutral-600)", marginTop: "6px", fontWeight: "500" }}>
                      Score &lt; 50
                    </div>
                  </div>
                  <div style={{ fontSize: "48px", opacity: 0.15 }}>⚠️</div>
                </div>
              </div>
            </sl-card>
          </div>

          {/* Module Cards Grid */}
          <div style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "20px", fontWeight: "600", marginBottom: "16px", color: "var(--sl-color-neutral-900)" }}>
              Module Details
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(450px, 1fr))", gap: "20px" }}>
              {adoptionData.modules.map((module) => (
                <sl-card key={module.module_key} style={{
                  "--border-radius": "var(--sl-border-radius-large)",
                  boxShadow: "var(--sl-shadow-large)"
                }}>
                  <div style={{ padding: "20px" }}>
                    {/* Module Header */}
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <sl-icon name={getModuleIcon(module.module_key)} style={{ fontSize: "32px", color: "var(--sl-color-primary-600)" }}></sl-icon>
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
                        <div style={{ fontSize: "24px", fontWeight: "bold", color: getScoreColor(module.adoption_score) }}>
                          {Math.round(module.adoption_score)}
                        </div>
                      )}
                    </div>

                    {/* Progress Bar */}
                    {module.adoption_score !== null && (
                      <sl-progress-bar
                        value={module.adoption_score}
                        style={{
                          "--height": "8px",
                          "--indicator-color": getScoreColor(module.adoption_score),
                          "--track-color": "var(--sl-color-neutral-200)",
                          marginBottom: "16px"
                        }}
                      ></sl-progress-bar>
                    )}

                    {/* Features Checklist */}
                    {module.features && module.features.length > 0 && (
                      <div style={{ marginBottom: "16px" }}>
                        {module.features.map((feature, idx) => (
                          <div key={idx} style={{ display: "flex", alignItems: "start", gap: "8px", padding: "8px 0", borderBottom: idx < module.features.length - 1 ? "1px solid var(--sl-color-neutral-200)" : "none" }}>
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
                              <div style={{ fontSize: "14px", fontWeight: "500", color: "var(--sl-color-neutral-900)" }}>
                                {feature.feature_name}
                              </div>
                              <div style={{ fontSize: "12px", color: "var(--sl-color-neutral-600)", marginTop: "2px" }}>
                                {feature.detail}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Recommendation */}
                    {module.top_recommendation && (
                      <sl-alert variant="neutral" open style={{ marginTop: "12px" }}>
                        <sl-icon slot="icon" name="lightbulb-fill"></sl-icon>
                        <strong>Recommendation:</strong> {module.top_recommendation}
                      </sl-alert>
                    )}
                  </div>
                </sl-card>
              ))}
            </div>
          </div>

          {/* Top Recommendations Panel */}
          {adoptionData.modules.some(m => m.licensed && m.adoption_score !== null && m.adoption_score < 80) && (
            <sl-card style={{
              "--border-radius": "var(--sl-border-radius-large)",
              boxShadow: "var(--sl-shadow-large)"
            }}>
              <div style={{ padding: "20px" }}>
                <h3 style={{ fontSize: "18px", fontWeight: "600", marginBottom: "16px", color: "var(--sl-color-neutral-900)" }}>
                  🎯 Top Actions to Improve Adoption
                </h3>
                <ol style={{ margin: 0, paddingLeft: "20px" }}>
                  {adoptionData.modules
                    .filter(m => m.licensed && m.adoption_score !== null && m.adoption_score < 80)
                    .sort((a, b) => a.adoption_score - b.adoption_score)
                    .map((module, idx) => (
                      <li key={idx} style={{ marginBottom: "12px", color: "var(--sl-color-neutral-900)" }}>
                        <strong>{module.module_name}:</strong> {module.top_recommendation}
                        <span style={{
                          marginLeft: "8px",
                          fontSize: "11px",
                          color: "var(--sl-color-neutral-600)",
                          padding: "2px 6px",
                          background: "var(--sl-color-neutral-100)",
                          borderRadius: "4px"
                        }}>
                          Impact: {module.adoption_score < 30 ? "High" : module.adoption_score < 60 ? "Medium" : "Low"}
                        </span>
                      </li>
                    ))}
                </ol>
              </div>
            </sl-card>
          )}
        </>
      )}
    </div>
  );
}

export { Home };
