/**
 * SentinelX-Shift Analyst Defense Console & Review Queue Client Logic
 * Simplified 5-Step Guided Demo Workflow:
 * 1. Choose a mode
 * 2. Run or ingest a scenario
 * 3. Review the alert
 * 4. See the outcome
 * 5. Reset when finished
 */

let currentAlerts = [];
let activeAlert = null;
let currentEnforcementConfig = null;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  initDashboard();
  setupEventListeners();
});

async function initDashboard() {
  await fetchSystemHealth();
  await fetchShadowMetrics();
  await fetchEnforcementState();
  await loadQueueAlerts();
}

function setupEventListeners() {
  // Step 3 Queue Filters
  const filterTier = document.getElementById("filter-tier");
  const filterFamily = document.getElementById("filter-family");
  const filterStatus = document.getElementById("filter-status");
  if (filterTier) filterTier.addEventListener("change", () => loadQueueAlerts());
  if (filterFamily) filterFamily.addEventListener("change", () => loadQueueAlerts());
  if (filterStatus) filterStatus.addEventListener("change", () => loadQueueAlerts());

  // Global Refresh
  const btnRefresh = document.getElementById("btn-refresh");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => {
      loadQueueAlerts();
      fetchShadowMetrics();
      fetchEnforcementState();
      showStatusBanner("info", "Data refreshed from SentinelX backend service.", null);
    });
  }

  // Step 2 Ingestion Buttons
  const btnSample = document.getElementById("btn-load-sample");
  if (btnSample) btnSample.addEventListener("click", () => handleLoadSampleTraffic());

  const btnP3 = document.getElementById("btn-load-phase3");
  if (btnP3) btnP3.addEventListener("click", () => handleLoadPhase3Demo());

  const btnReplay = document.getElementById("btn-shadow-replay");
  if (btnReplay) btnReplay.addEventListener("click", () => handleShadowReplay());

  // Step 1 Mode Switchers
  const tabM1 = document.getElementById("tab-mode-1");
  const tabM2 = document.getElementById("tab-mode-2");
  if (tabM1) tabM1.addEventListener("click", () => switchOperatingMode("MODE_1_REAL_SITE"));
  if (tabM2) tabM2.addEventListener("click", () => switchOperatingMode("MODE_2_REPLICA_DEFENSE"));

  // Step 1 Global Blocking & Emergency Stop
  const btnGlobal = document.getElementById("btn-toggle-global-blocking");
  const btnEmerg = document.getElementById("btn-emergency-stop");
  if (btnGlobal) btnGlobal.addEventListener("click", () => toggleGlobalBlocking());
  if (btnEmerg) btnEmerg.addEventListener("click", () => toggleEmergencyStop());

  // Step 2 Scenario Execution Triggers
  const btnBrute = document.getElementById("btn-run-scenario-bruteforce");
  const btnBenign = document.getElementById("btn-run-scenario-benign");
  const btnHoney = document.getElementById("btn-run-scenario-honeypot");
  if (btnBrute) btnBrute.addEventListener("click", () => handleRunScenario("bruteforce"));
  if (btnBenign) btnBenign.addEventListener("click", () => handleRunScenario("benign_burst"));
  if (btnHoney) btnHoney.addEventListener("click", () => handleRunScenario("honeypot"));

  // Step 5 Reset Scenario Trigger
  const btnReset = document.getElementById("btn-reset-scenario");
  if (btnReset) btnReset.addEventListener("click", () => handleResetScenario());

  // Step 3 Modal Controls
  const modalClose = document.getElementById("modal-close-btn");
  const modalBackdrop = document.getElementById("modal-backdrop");
  if (modalClose) modalClose.addEventListener("click", () => closeModal());
  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", (e) => {
      if (e.target === modalBackdrop) closeModal();
    });
  }

  // Triage Action Buttons inside Modal
  document.querySelectorAll(".triage-buttons-grid button").forEach(btn => {
    btn.addEventListener("click", () => {
      const action = btn.getAttribute("data-action");
      handleTriageAction(action);
    });
  });

  // Workflow navigation step clicks
  document.querySelectorAll(".workflow-step").forEach((stepEl, idx) => {
    stepEl.addEventListener("click", () => {
      highlightWorkflowStep(idx + 1);
    });
  });
}

// -------------------------------------------------------------
// Workflow Visual Guidance & Inline Notification Helpers
// -------------------------------------------------------------

function highlightWorkflowStep(stepNum) {
  for (let i = 1; i <= 5; i++) {
    const el = document.getElementById(`wf-step-${i}`);
    if (el) {
      if (i === stepNum) el.classList.add("active");
      else el.classList.remove("active");
    }
  }
}

function showStatusBanner(type, message, nextHint) {
  const banner = document.getElementById("scenario-status-banner");
  const textEl = document.getElementById("scenario-status-text");
  const hintEl = document.getElementById("workflow-next-hint");

  if (!banner || !textEl) return;

  banner.className = `status-banner status-banner-${type}`;
  textEl.innerHTML = message;
  banner.style.display = "flex";

  if (hintEl && nextHint) {
    hintEl.innerHTML = `<strong>Next Action:</strong> ${nextHint}`;
  }
}

function closeStatusBanner() {
  const banner = document.getElementById("scenario-status-banner");
  if (banner) banner.style.display = "none";
}
window.closeStatusBanner = closeStatusBanner;

// -------------------------------------------------------------
// System Health & Queue Alerts (Step 3)
// -------------------------------------------------------------

async function fetchSystemHealth() {
  try {
    const res = await fetch("/health");
    if (res.ok) {
      const data = await res.json();
      const modelDisplay = document.getElementById("model-name-display");
      if (modelDisplay) {
        modelDisplay.textContent = `${data.loaded_model} (Monitor-Only)`;
      }
      updateKpis(data.queue_stats);
    }
  } catch (err) {
    console.error("Failed to load health status:", err);
  }
}

async function loadQueueAlerts() {
  const tierEl = document.getElementById("filter-tier");
  const familyEl = document.getElementById("filter-family");
  const statusEl = document.getElementById("filter-status");

  const tier = tierEl ? tierEl.value : "";
  const family = familyEl ? familyEl.value : "";
  const status = statusEl ? statusEl.value : "";

  const params = new URLSearchParams();
  if (tier) params.append("risk_tier", tier);
  if (family) params.append("suspected_family", family);
  if (status) params.append("review_status", status);

  try {
    const res = await fetch(`/api/v1/alerts?${params.toString()}`);
    if (res.ok) {
      const data = await res.json();
      currentAlerts = data.alerts;
      updateKpis(data.queue_stats);
      renderAlertFeed(data.alerts);
      const countLabel = document.getElementById("queue-count-label");
      if (countLabel) {
        countLabel.textContent = `Showing ${data.alerts.length} of ${data.total_matching} alerts`;
      }
    }
  } catch (err) {
    console.error("Failed to load alerts:", err);
  }
}

function updateKpis(stats) {
  if (!stats) return;
  const setEl = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };
  setEl("val-total", stats.total_alerts || 0);
  setEl("val-pending", stats.pending_review || 0);
  setEl("val-high-priority", stats.high_priority || 0);
  setEl("val-confirmed", stats.confirmed_incidents || 0);
  setEl("val-suppressed", stats.suppressed_benign || 0);
}

function renderAlertFeed(alerts) {
  const container = document.getElementById("alerts-container");
  if (!container) return;

  if (!alerts || alerts.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <p>No alerts matching the selected filters. Click <strong>"Ingest Sample Traffic"</strong> in Step 2 or run a scenario.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = alerts.map(item => {
    const a = item.alert;
    const tierClass = `card-${a.risk_tier.toLowerCase()}`;
    const scorePct = Math.round(a.scores.production_score * 100);

    // Color for score bar
    let barColor = "#10b981";
    if (a.scores.production_score >= 0.8) barColor = "#ef4444";
    else if (a.scores.production_score >= 0.6) barColor = "#f97316";
    else if (a.scores.production_score >= 0.3) barColor = "#eab308";

    // Confirming signal summary
    let signalSummary = '<span class="signal-pill signal-unavailable">Telemetry: Unavailable</span>';
    const confSignals = Object.values(a.confirming_signals || {}).filter(s => s.present);
    if (confSignals.length > 0) {
      const anyConfirmed = confSignals.some(s => s.confirmed === true);
      if (anyConfirmed) {
        signalSummary = `<span class="signal-pill signal-confirmed">Signals Confirmed (${confSignals.length})</span>`;
      } else {
        signalSummary = `<span class="signal-pill signal-unavailable">Signals Observed (${confSignals.length})</span>`;
      }
    }

    const statusClass = `status-${item.review_status.toLowerCase()}`;
    const statusText = item.review_status.replace(/_/g, " ");

    const shortUuid = a.alert_id.substring(0, 8);
    const dateObj = new Date(a.timestamp);
    const readableTime = !isNaN(dateObj.getTime())
      ? dateObj.toISOString().replace("T", " ").substring(0, 19) + " UTC"
      : a.timestamp;
    const batchPill = a.batch_id ? `<span class="batch-pill">${escapeHtml(a.batch_id)}</span>` : "";

    return `
      <div class="alert-card ${tierClass}">
        <div class="card-primary-col">
          <div class="card-flow-id">
            <span class="flow-name">${escapeHtml(a.flow_id || "Flow")}</span>
            <span class="alert-uuid-pill">#${escapeHtml(shortUuid)}</span>
            ${batchPill}
          </div>
          <div class="card-meta-row">
            <span class="card-timestamp">${escapeHtml(readableTime)}</span>
            <span>&bull;</span>
            <span>Family: <strong>${escapeHtml(a.suspected_family || "Benign / General")}</strong></span>
            <span>&bull;</span>
            <span>Rec: <em>${escapeHtml(a.recommended_action)}</em></span>
          </div>
        </div>

        <div class="card-scores-col">
          <div class="score-bar-wrapper">
            <div class="score-bar-bg">
              <div class="score-bar-fill" style="width: ${scorePct}%; background-color: ${barColor};"></div>
            </div>
            <span class="score-num" style="color: ${barColor};">${a.scores.production_score.toFixed(4)}</span>
          </div>
          <div class="scores-sub">AE: ${a.scores.autoencoder_score.toFixed(3)} | XGB: ${a.scores.supervised_score.toFixed(3)}</div>
        </div>

        <div class="card-signals-col">
          <div>${signalSummary}</div>
          <div style="font-size: 0.75rem; color: #94a3b8;">${escapeHtml(a.policy_notes[0] || "")}</div>
        </div>

        <div class="card-status-col">
          <span class="status-badge ${statusClass}">${statusText}</span>
        </div>

        <div style="text-align: right;">
          <button class="btn btn-secondary" onclick="openAlertDetail('${a.alert_id}')">
            Inspect &amp; Triage
          </button>
        </div>
      </div>
    `;
  }).join("");
}

function openAlertDetail(alertId) {
  const item = currentAlerts.find(i => i.alert.alert_id === alertId);
  if (!item) return;

  activeAlert = item;
  const a = item.alert;

  const batchStr = a.batch_id ? ` | Batch: ${a.batch_id}` : '';
  document.getElementById("modal-alert-id").textContent = `Alert UUID: ${a.alert_id} | Flow: ${a.flow_id || 'N/A'}${batchStr} | Ingested: ${a.timestamp}`;
  document.getElementById("modal-prod-score").textContent = a.scores.production_score.toFixed(4);
  document.getElementById("modal-ae-score").textContent = a.scores.autoencoder_score.toFixed(4);
  document.getElementById("modal-xgb-score").textContent = a.scores.supervised_score.toFixed(4);
  document.getElementById("modal-gated-active").textContent = a.scores.gated_activation ? "ACTIVE (+0.41)" : "Inactive";
  document.getElementById("modal-gated-active").style.color = a.scores.gated_activation ? "#ef4444" : "#94a3b8";

  // Signals table
  const tbodySignals = document.getElementById("modal-signals-table-body");
  const signals = a.confirming_signals || {};
  tbodySignals.innerHTML = Object.keys(signals).map(key => {
    const s = signals[key];
    const statusText = s.present ? (s.confirmed ? '<strong style="color: #ef4444;">CONFIRMED</strong>' : '<span style="color: #94a3b8;">Negative</span>') : '<em style="color: #64748b;">UNAVAILABLE</em>';
    const valText = s.present ? (s.value !== null ? s.value : 'Present') : 'N/A';
    return `
      <tr>
        <td><strong>${escapeHtml(s.signal_name)}</strong></td>
        <td>${s.present ? 'Present' : 'Not Provided'}</td>
        <td>${escapeHtml(String(valText))}</td>
        <td>${escapeHtml(String(s.threshold || 'N/A'))}</td>
        <td>${statusText}</td>
        <td>${escapeHtml(s.description)}</td>
      </tr>
    `;
  }).join("");

  // Policy notes
  const notesUl = document.getElementById("modal-policy-notes");
  notesUl.innerHTML = (a.policy_notes || []).map(n => `<li>${escapeHtml(n)}</li>`).join("");

  // Telemetry table
  const tbodyTelem = document.getElementById("modal-telemetry-table-body");
  const telem = item.flow_telemetry || {};
  const keys = Object.keys(telem);
  if (keys.length === 0) {
    tbodyTelem.innerHTML = `<tr><td colspan="2" style="text-align: center; color: #64748b;">No raw flow telemetry stored for this record.</td></tr>`;
  } else {
    tbodyTelem.innerHTML = keys.map(k => `
      <tr>
        <td><code>${escapeHtml(k)}</code></td>
        <td style="font-family: monospace;">${escapeHtml(String(telem[k]))}</td>
      </tr>
    `).join("");
  }

  // Pre-fill notes if already reviewed
  const notesField = document.getElementById("analyst-notes");
  notesField.value = item.latest_review ? (item.latest_review.notes || "") : "";

  document.getElementById("modal-backdrop").style.display = "flex";
}
window.openAlertDetail = openAlertDetail;

function closeModal() {
  document.getElementById("modal-backdrop").style.display = "none";
  activeAlert = null;
}

async function handleTriageAction(action) {
  if (!activeAlert) return;
  const alertId = activeAlert.alert.alert_id;
  const notes = document.getElementById("analyst-notes").value;

  try {
    const res = await fetch(`/api/v1/alerts/${alertId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: action,
        analyst_id: "sec-analyst-1",
        notes: notes
      })
    });

    if (res.ok) {
      closeModal();
      await loadQueueAlerts();
      await fetchSystemHealth();
      showStatusBanner(
        "success",
        `Analyst triage recorded: <strong>${action.replace(/_/g, " ")}</strong> for Alert <code>${alertId.substring(0, 8)}</code>. SOC database updated.`,
        "Step 4: Inspect the outcome below, or click Step 5 to reset the scenario."
      );
      highlightWorkflowStep(4);
    } else {
      showStatusBanner("error", "Failed to record analyst review decision.", null);
    }
  } catch (err) {
    console.error("Error submitting review action:", err);
    showStatusBanner("error", "Network error submitting review decision.", null);
  }
}

// -------------------------------------------------------------
// Step 2: Background Ingestion Actions
// -------------------------------------------------------------

async function handleLoadSampleTraffic() {
  const btn = document.getElementById("btn-load-sample");
  const origText = btn ? btn.textContent : "Ingest Sample Traffic";
  try {
    if (btn) {
      btn.textContent = "Ingesting...";
      btn.disabled = true;
    }

    const res = await fetch("/api/v1/queue/load_sample", { method: "POST" });
    if (res.ok) {
      await loadQueueAlerts();
      await fetchSystemHealth();
      showStatusBanner(
        "info",
        "Sample netflow traffic ingested successfully into the analyst review queue.",
        "Step 3: Review incoming alerts in the prioritized queue below."
      );
      highlightWorkflowStep(3);
    }
  } catch (err) {
    console.error("Failed to load sample traffic:", err);
    showStatusBanner("error", "Failed to load sample traffic.", null);
  } finally {
    if (btn) {
      btn.textContent = origText;
      btn.disabled = false;
    }
  }
}

async function handleLoadPhase3Demo() {
  const btn = document.getElementById("btn-load-phase3");
  const origText = btn ? btn.textContent : "Ingest Phase 3 Correlated Logs";
  try {
    if (btn) {
      btn.textContent = "Correlating Logs...";
      btn.disabled = true;
    }

    const res = await fetch("/api/v1/demo/phase3?force=true", { method: "POST" });
    if (res.ok) {
      await fetchSystemHealth();
      await loadQueueAlerts();
      showStatusBanner(
        "info",
        "Phase 3 synthetic Nginx access/error and ModSecurity logs correlated with netflow events.",
        "Step 3: Review correlated multi-source alerts in the queue below."
      );
      highlightWorkflowStep(3);
    } else {
      showStatusBanner("error", "Failed to run Phase 3 demo.", null);
    }
  } catch (err) {
    console.error("Failed to run Phase 3 demo:", err);
    showStatusBanner("error", "Network error running Phase 3 demo.", null);
  } finally {
    if (btn) {
      btn.textContent = origText;
      btn.disabled = false;
    }
  }
}

async function handleShadowReplay() {
  const btn = document.getElementById("btn-shadow-replay");
  if (!btn) return;
  const origText = btn.textContent;
  try {
    btn.textContent = "Running Replay...";
    btn.disabled = true;

    const res = await fetch("/api/v1/shadow/replay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset: "synthetic", batch_size: 32 })
    });

    if (res.ok) {
      await fetchShadowMetrics();
      await fetchSystemHealth();
      await loadQueueAlerts();
      showStatusBanner(
        "info",
        "Shadow evaluation completed in monitor-only mode. Zero network commands dispatched.",
        "Step 3: Review updated queue alerts."
      );
      highlightWorkflowStep(3);
    } else {
      showStatusBanner("error", "Failed to run shadow replay.", null);
    }
  } catch (err) {
    console.error("Shadow replay error:", err);
    showStatusBanner("error", "Network error running shadow replay.", null);
  } finally {
    btn.textContent = origText;
    btn.disabled = false;
  }
}

function escapeHtml(str) {
  if (typeof str !== "string") return str;
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function fetchShadowMetrics() {
  const latencyEl = document.getElementById("obs-latency");
  const alertsRateEl = document.getElementById("obs-alerts-hr");
  const qualityEl = document.getElementById("obs-quality");
  const driftEl = document.getElementById("obs-drift");

  if (!latencyEl) return;

  try {
    const res = await fetch("/api/v1/shadow/metrics");
    if (res.ok) {
      const data = await res.json();
      const snap = data.snapshot;
      if (!snap) {
        latencyEl.textContent = "N/A (Ready)";
        alertsRateEl.textContent = "0.0/hr";
        qualityEl.textContent = "0 misses / 0 invalid";
        driftEl.innerHTML = '<span class="badge" style="background-color: #334155; color: #94a3b8;">No data</span>';
        return;
      }

      if (snap.latency) {
        latencyEl.textContent = `${snap.latency.p50_ms.toFixed(2)} ms / ${snap.latency.p95_ms.toFixed(2)} ms`;
      }
      alertsRateEl.textContent = `${snap.alerts_per_hour.toFixed(1)}/hr`;
      if (snap.quality_counters) {
        qualityEl.textContent = `${snap.quality_counters.correlation_misses} misses / ${snap.quality_counters.invalid_records} invalid`;
      }

      const scoreDrift = snap.score_drift && snap.score_drift.status === "drift_detected";
      const featDrift = snap.feature_drift && snap.feature_drift.status === "drift_detected";

      if (scoreDrift || featDrift) {
        driftEl.innerHTML = '<span class="badge" style="background-color: #b45309; color: #fef08a;">Drift Flagged</span>';
      } else {
        driftEl.innerHTML = '<span class="badge" style="background-color: #065f46; color: #6ee7b7;">Stable</span>';
      }
    }
  } catch (err) {
    console.error("Failed to load shadow metrics:", err);
  }
}

// -------------------------------------------------------------
// Step 1: Operating Modes & Safety Controls Logic
// -------------------------------------------------------------

async function fetchEnforcementState() {
  try {
    const [cfgRes, blocksRes, auditRes] = await Promise.all([
      fetch("/api/v1/enforcement/config"),
      fetch("/api/v1/enforcement/blocks"),
      fetch("/api/v1/enforcement/audit?limit=5")
    ]);

    if (!cfgRes.ok) return;

    currentEnforcementConfig = await cfgRes.json();
    const blocksData = blocksRes.ok ? await blocksRes.json() : { active_blocks: [], count: 0 };
    const auditData = auditRes.ok ? await auditRes.json() : { audit_trail: [], count: 0 };

    renderEnforcementHeader(currentEnforcementConfig, blocksData);
    renderActiveBlocks(blocksData.blocks || blocksData.active_blocks || []);
    renderAuditTrail(auditData.records || auditData.audit_trail || []);
  } catch (err) {
    console.error("Failed to load enforcement state:", err);
  }
}

function renderEnforcementHeader(config, blocksData) {
  const tabM1 = document.getElementById("tab-mode-1");
  const tabM2 = document.getElementById("tab-mode-2");
  const card1 = document.getElementById("mode-card-1");
  const card2 = document.getElementById("mode-card-2");
  const badgeMode = document.getElementById("current-mode-badge");
  const bannerInfo = document.getElementById("mode-banner-info");
  const btnGlobal = document.getElementById("btn-toggle-global-blocking");
  const textGlobal = document.getElementById("global-blocking-status-text");
  const btnEmerg = document.getElementById("btn-emergency-stop");
  const blocksCountEl = document.getElementById("val-active-blocks-count");

  if (blocksCountEl) {
    const countVal = blocksData.count ?? (blocksData.blocks ? blocksData.blocks.length : (blocksData.active_blocks ? blocksData.active_blocks.length : 0));
    blocksCountEl.textContent = countVal;
  }

  const isMode1 = config.operating_mode === "MODE_1_REAL_SITE";

  if (tabM1 && tabM2) {
    if (isMode1) {
      tabM1.className = "mode-tab-btn active-mode-1";
      tabM2.className = "mode-tab-btn";
    } else {
      tabM1.className = "mode-tab-btn";
      tabM2.className = "mode-tab-btn active-mode-2";
    }
  }

  if (card1 && card2) {
    if (isMode1) {
      card1.classList.add("active-card");
      card2.classList.remove("active-card");
    } else {
      card1.classList.remove("active-card");
      card2.classList.add("active-card");
    }
  }

  if (badgeMode) {
    if (isMode1) {
      badgeMode.className = "status-badge-simulated";
      badgeMode.textContent = "MODE 1: REAL-SITE MONITORING (SIMULATED / NOT CONNECTED)";
    } else {
      badgeMode.className = "status-badge-replica";
      badgeMode.textContent = "MODE 2: REPLICA DEFENSE (LOCAL LAB)";
    }
  }

  if (bannerInfo) {
    if (isMode1) {
      bannerInfo.innerHTML = `<strong>Mode 1 (Authorized Real-Site Monitoring):</strong> Operating passively against production site <code>prod-portal-alpha</code>. Enforcement adapter is <code>MockRealSiteAdapter</code> (<span class="status-badge-simulated">SIMULATED / NOT CONNECTED</span> - Zero real network or firewall commands dispatched). Model scores alone cannot block; independent attack evidence and per-site authorization are strictly mandatory.`;
    } else {
      bannerInfo.innerHTML = `<strong>Mode 2 (Isolated Replica Defense):</strong> Operating against dedicated local replica testbed at <a href="/replica" target="_blank" style="color: #60a5fa; text-decoration: underline;"><code>/replica</code></a>. Enforcement adapter is <code>LocalReplicaAdapter</code> (<span class="status-badge-replica">REPLICA</span> - Local memory interceptor). Lab allowlists and policies are strictly isolated from Mode 1.`;
    }
  }

  if (btnGlobal && textGlobal) {
    if (config.global_blocking_enabled) {
      btnGlobal.className = "btn-toggle-blocking blocking-on";
      textGlobal.textContent = "ON";
    } else {
      btnGlobal.className = "btn-toggle-blocking";
      textGlobal.textContent = "OFF";
    }
  }

  if (btnEmerg) {
    if (config.emergency_stop_active) {
      btnEmerg.classList.add("active");
      btnEmerg.textContent = "EMERGENCY STOP ACTIVE";
    } else {
      btnEmerg.classList.remove("active");
      btnEmerg.textContent = "EMERGENCY STOP";
    }
  }
}

async function switchOperatingMode(mode) {
  try {
    const res = await fetch("/api/v1/enforcement/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operating_mode: mode })
    });
    if (res.ok) {
      await fetchEnforcementState();
      const modeLabel = mode === "MODE_1_REAL_SITE" ? "Mode 1 (Real-Site Passive Monitoring)" : "Mode 2 (Local Replica Defense Lab)";
      showStatusBanner(
        "info",
        `Switched operating mode to <strong>${modeLabel}</strong>.`,
        "Step 2: Choose a scenario below to run defense simulation or ingest background traffic."
      );
      highlightWorkflowStep(2);
    }
  } catch (err) {
    console.error("Failed to switch operating mode:", err);
  }
}

async function toggleGlobalBlocking() {
  if (!currentEnforcementConfig) return;
  const target = !currentEnforcementConfig.global_blocking_enabled;
  try {
    const res = await fetch("/api/v1/enforcement/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ global_blocking_enabled: target })
    });
    if (res.ok) {
      await fetchEnforcementState();
      await fetchSystemHealth();
      showStatusBanner(
        "info",
        `Global Autonomous Blocking set to <strong>${target ? "ON" : "OFF"}</strong>.`,
        null
      );
    }
  } catch (err) {
    console.error("Failed to toggle global blocking:", err);
  }
}

async function toggleEmergencyStop() {
  if (!currentEnforcementConfig) return;
  const target = !currentEnforcementConfig.emergency_stop_active;
  try {
    const res = await fetch("/api/v1/enforcement/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ emergency_stop_active: target })
    });
    if (res.ok) {
      await fetchEnforcementState();
      await fetchSystemHealth();
      showStatusBanner(
        target ? "error" : "info",
        `Emergency Circuit Breaker: <strong>${target ? "ACTIVATED (All blocks released, defense paused)" : "DEACTIVATED (Normal defense restored)"}</strong>.`,
        null
      );
    }
  } catch (err) {
    console.error("Failed to toggle emergency stop:", err);
  }
}

// -------------------------------------------------------------
// Step 2 & 4: Scenario Execution & Outcome Logic
// -------------------------------------------------------------

async function handleRunScenario(scenarioName) {
  const btnId = scenarioName === "bruteforce"
    ? "btn-run-scenario-bruteforce"
    : (scenarioName === "benign_burst" ? "btn-run-scenario-benign" : "btn-run-scenario-honeypot");
  const btn = document.getElementById(btnId);
  const origText = btn ? btn.textContent : "";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Running...";
  }

  try {
    const res = await fetch("/api/v1/replica/scenarios/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: scenarioName })
    });

    if (res.ok) {
      const data = await res.json();
      await fetchEnforcementState();
      await loadQueueAlerts();
      await fetchSystemHealth();

      const r = data.result || data || {};
      const actionVal = r.action || r.decision?.action || "EVALUATED";
      const statusVal = r.status || r.decision?.status || "REPLICA";

      if (scenarioName === "bruteforce") {
        showStatusBanner(
          "success",
          `<strong>Scenario 1 Executed:</strong> Credential spray against <code>${r.target_route || "/replica/login"}</code> triggered confirmed brute force defense. Attacker <code>${r.attacker_ip || r.target_ip}</code> is <strong>BLOCKED</strong> (HTTP 403 Forbidden verified, 60s TTL).`,
          "Step 3: Review the alert in the prioritized queue below, or proceed to Step 4 to view the active block."
        );
        highlightWorkflowStep(3);
      } else if (scenarioName === "honeypot") {
        showStatusBanner(
          "success",
          `<strong>Scenario 2 Executed:</strong> Probe against hidden route <code>${r.target_route || "/replica/admin-decoy"}</code> triggered the honeypot trap. Confirmed decoy interaction caused immediate in-process defense. Attacker <code>${r.attacker_ip || r.target_ip}</code> is <strong>BLOCKED</strong> (HTTP 403 Forbidden verified, 60s TTL).`,
          "Step 3: Review the confirmed honeypot alert below, or proceed to Step 4 to view the active block."
        );
        highlightWorkflowStep(3);
      } else {
        showStatusBanner(
          "info",
          `<strong>Scenario 3 Executed:</strong> Administrative burst from trusted client <code>${r.admin_ip || r.target_ip}</code> to <code>${r.target_route || "/replica/portal"}</code> matched trusted allowlist. <strong>ALLOWLISTED_BYPASS</strong> applied &mdash; traffic permitted without blocking (HTTP 200 OK verified).`,
          "Step 4: Check Active Ephemeral Blocks below to confirm zero false-positive blocks were created."
        );
        highlightWorkflowStep(4);
      }
    } else {
      showStatusBanner("error", `Failed to run scenario '${scenarioName}'.`, null);
    }
  } catch (err) {
    console.error("Error running scenario:", err);
    showStatusBanner("error", "Network error running scenario.", null);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = origText;
    }
  }
}

// -------------------------------------------------------------
// Step 4: Active Blocks & Audit Trail Rendering
// -------------------------------------------------------------

function renderActiveBlocks(blocks) {
  const container = document.getElementById("active-blocks-container");
  if (!container) return;

  if (blocks.length === 0) {
    container.innerHTML = `<p style="font-size: 0.85rem; color: var(--text-muted);">No active blocks. (All traffic permitted).</p>`;
    return;
  }

  let html = `<div style="display: flex; flex-direction: column; gap: 8px;">`;
  blocks.forEach(b => {
    const ip = b.target_ip || b.ip_address || "unknown";
    const statusVal = b.status || (b.is_simulated ? "SIMULATED" : "REPLICA");
    const badgeClass = statusVal === "SIMULATED" ? "status-badge-simulated" : (statusVal === "REPLICA" ? "status-badge-replica" : "status-badge-blocked");
    const statusLabel = statusVal === "SIMULATED" ? "SIMULATED / NOT CONNECTED" : statusVal;

    let ttlRemaining = b.ttl_remaining_seconds;
    if (ttlRemaining === undefined && b.expires_at) {
      ttlRemaining = Math.max(0, Math.round((new Date(b.expires_at) - new Date()) / 1000));
    }
    if (ttlRemaining === undefined) ttlRemaining = b.ttl_seconds || 60;

    html += `
      <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.6); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border-color);">
        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
          <span class="${badgeClass}">${statusLabel}</span>
          <strong style="font-family: var(--font-mono);">${ip}</strong>
          <span style="font-size: 0.8rem; color: var(--text-secondary);">Site: <code>${b.site_id || "N/A"}</code></span>
          <span style="font-size: 0.8rem; color: var(--text-muted);">${b.reason || "Active temporary block"}</span>
          <span style="font-size: 0.8rem; color: #fbbf24; font-weight: 600;">TTL: ${ttlRemaining}s remaining</span>
        </div>
        <div>
          <button class="btn-scenario btn-scenario-secondary" style="padding: 4px 10px; font-size: 0.75rem;" onclick="handleReleaseBlock('${ip}', '${b.site_id || ""}')">Release Block</button>
        </div>
      </div>
    `;
  });
  html += `</div>`;
  container.innerHTML = html;
}

function formatEvidenceSummary(evidence) {
  if (!evidence) return '<span style="color: var(--text-muted);">None (Model only)</span>';
  if (Array.isArray(evidence)) {
    if (evidence.length === 0) return '<span style="color: var(--text-muted);">None (Model only)</span>';
    return evidence.map(item => {
      if (item.includes("honeypot_interaction: CONFIRMED")) {
        return `<code style="background: rgba(217, 119, 6, 0.25); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); padding: 2px 5px; border-radius: 3px; font-weight: 600;">[HONEYPOT DECOY] ${item}</code>`;
      }
      return `<code style="background: rgba(30,41,59,0.7); padding: 1px 4px; border-radius: 3px;">${item}</code>`;
    }).join("<br>");
  }
  if (typeof evidence === "string") return evidence;
  const entries = Object.entries(evidence);
  if (entries.length === 0) return '<span style="color: var(--text-muted);">None</span>';
  return entries.map(([k, v]) => `<code>${k}=${v}</code>`).join(", ");
}

function getStatusBadgeClass(status) {
  if (status === "SIMULATED") return "status-badge-simulated";
  if (status === "REPLICA") return "status-badge-replica";
  if (status === "UNAVAILABLE") return "status-badge-unavailable";
  return "badge";
}

function renderAuditTrail(events) {
  const tbody = document.getElementById("audit-table-body");
  if (!tbody) return;

  if (events.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 16px;">
          No enforcement events recorded yet. Run a scenario in Step 2 to generate events.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = events.map(e => {
    const timeStr = new Date(e.timestamp).toLocaleTimeString();
    const actionClass = e.action === "BLOCK" ? "badge-critical" : "badge-low";
    const statusVal = e.status;
    const statusClass = getStatusBadgeClass(statusVal);
    const statusLabel = statusVal === "SIMULATED" ? "SIMULATED / NOT CONNECTED" : statusVal;
    const ip = e.target_ip || e.ip_address || "N/A";
    const route = e.target_route || (e.site_id && e.site_id.includes('replica') ? '/replica/login' : '/login');
    const attack = e.suspected_attack || e.suspected_family || "Unknown";
    const scoreVal = (e.model_score !== undefined) ? e.model_score : (e.risk_score !== undefined ? e.risk_score : null);
    const riskStr = (scoreVal !== null && scoreVal !== undefined) ? Number(scoreVal).toFixed(3) : "N/A";
    const evSummary = formatEvidenceSummary(e.evidence_summary);

    return `
      <tr>
        <td style="font-family: var(--font-mono); font-size: 0.8rem; white-space: nowrap;">${timeStr}</td>
        <td>
          <code>${e.site_id || "N/A"}</code><br>
          <span style="font-size: 0.75rem; color: #93c5fd;">Route: <code>${route}</code></span>
        </td>
        <td>
          <strong style="font-family: var(--font-mono);">${ip}</strong><br>
          <span class="geo-privacy-pill">Protected (No Geo-IP inferred)</span>
        </td>
        <td>
          <strong>${attack}</strong><br>
          <small style="color: var(--text-muted);">Score: ${riskStr}</small>
        </td>
        <td style="font-size: 0.78rem;">${evSummary}</td>
        <td>
          <span class="badge ${actionClass}">${e.action}</span>
          <span class="${statusClass}" style="margin-left: 4px;">${statusLabel}</span>
        </td>
        <td style="font-size: 0.82rem; color: var(--text-secondary); max-width: 260px;">${e.reason || "N/A"}</td>
      </tr>
    `;
  }).join("");
}

async function handleReleaseBlock(ip, siteId) {
  try {
    const res = await fetch("/api/v1/enforcement/blocks/release", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_ip: ip, ip_address: ip, site_id: siteId })
    });
    if (res.ok) {
      await fetchEnforcementState();
      showStatusBanner(
        "info",
        `Manual release: Ephemeral block on <code>${ip}</code> released immediately.`,
        "Step 5: Click Reset Demo Scenario when finished."
      );
      highlightWorkflowStep(5);
    }
  } catch (err) {
    console.error("Failed to release block:", err);
    showStatusBanner("error", "Failed to release block.", null);
  }
}
window.handleReleaseBlock = handleReleaseBlock;

// -------------------------------------------------------------
// Step 5: Reset Demo Scenario State
// -------------------------------------------------------------

async function handleResetScenario() {
  const btn = document.getElementById("btn-reset-scenario");
  const origText = btn ? btn.textContent : "";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Resetting...";
  }

  try {
    const res = await fetch("/api/v1/replica/scenarios/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });

    if (res.ok) {
      const data = await res.json();
      await fetchEnforcementState();
      await loadQueueAlerts();
      await fetchSystemHealth();

      showStatusBanner(
        "success",
        "<strong>Reset Completed:</strong> Ephemeral test blocks on the local replica have been cleared. Baseline replica state restored. (Analyst review database and historical audit records were preserved).",
        "Step 1 or 2: Choose another scenario to test defense behavior."
      );
      highlightWorkflowStep(1);
    } else {
      showStatusBanner("error", "Failed to reset demo scenario.", null);
    }
  } catch (err) {
    console.error("Failed to reset scenario:", err);
    showStatusBanner("error", "Network error while resetting demo scenario.", null);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = origText;
    }
  }
}
