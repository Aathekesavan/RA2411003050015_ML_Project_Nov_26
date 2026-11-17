/**
 * SentinelX Mode 2 Active-Scenario Presentation Console Client Logic
 * Synchronizes local replica view with SentinelX Guard inspector,
 * 3-step progress pipeline, floating centered status card, and countdown timer.
 */

let currentScenario = "bruteforce";
let isRunning = false;
let isPaused = false;
let countdownTimer = null;
let currentTtl = 15;
let initialTtl = 15;
let stepTimeouts = [];

document.addEventListener("DOMContentLoaded", () => {
  initPresentation();
  setupEventListeners();
});

function setupEventListeners() {
  const selectScen = document.getElementById("select-scenario");
  if (selectScen) {
    selectScen.addEventListener("change", (e) => {
      currentScenario = e.target.value;
      handleScenarioChange();
    });
  }

  const btnStart = document.getElementById("btn-start");
  if (btnStart) {
    btnStart.addEventListener("click", () => handleStartScenario());
  }

  const btnPause = document.getElementById("btn-pause");
  if (btnPause) {
    btnPause.addEventListener("click", () => handlePauseScenario());
  }

  const btnReset = document.getElementById("btn-reset");
  if (btnReset) {
    btnReset.addEventListener("click", () => handleResetScenario());
  }

  const btnDismiss = document.getElementById("btn-dismiss-overlay");
  if (btnDismiss) {
    btnDismiss.addEventListener("click", () => {
      const overlay = document.getElementById("interception-overlay");
      if (overlay) overlay.style.display = "none";
    });
  }

  const btnTopDismiss = document.getElementById("btn-top-dismiss-overlay");
  if (btnTopDismiss) {
    btnTopDismiss.addEventListener("click", () => {
      const overlay = document.getElementById("interception-overlay");
      if (overlay) overlay.style.display = "none";
    });
  }

  // Dismiss by clicking outside the card on the backdrop
  const overlayBackdrop = document.getElementById("interception-overlay");
  if (overlayBackdrop) {
    overlayBackdrop.addEventListener("click", (e) => {
      if (e.target === overlayBackdrop) {
        overlayBackdrop.style.display = "none";
      }
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const overlay = document.getElementById("interception-overlay");
      if (overlay && overlay.style.display === "flex") {
        overlay.style.display = "none";
      }
    }
  });
}

function updateStepTitles(scenarioName) {
  const t1 = document.getElementById("stage1-title");
  const t2 = document.getElementById("stage2-title");
  const t3 = document.getElementById("stage3-title");

  if (scenarioName === "honeypot") {
    if (t1) t1.textContent = "Decoy route accessed";
    if (t2) t2.textContent = "Honeypot interaction confirmed";
    if (t3) t3.textContent = "Simulated source blocked in local replica";
  } else if (scenarioName === "benign_burst") {
    if (t1) t1.textContent = "Traffic evaluated";
    if (t2) t2.textContent = "Allowlist matched";
    if (t3) t3.textContent = "Allowlist bypass permitted";
  } else {
    // bruteforce or default
    if (t1) t1.textContent = "Attack detected";
    if (t2) t2.textContent = "Evidence confirmed";
    if (t3) t3.textContent = "Temporary block active";
  }
}

async function initPresentation() {
  updateStepTitles(currentScenario);
  updateViewportContent(currentScenario);
  await loadScenarioComparison(currentScenario);
}

function handleScenarioChange() {
  clearAllTimers();
  isRunning = false;
  isPaused = false;
  updateButtonStates();
  updateStepTitles(currentScenario);
  resetStagesToPending();
  hideInterceptionOverlay();
  updateViewportContent(currentScenario);
  loadScenarioComparison(currentScenario);
}

function updateViewportContent(scenarioName) {
  const contentEl = document.getElementById("replica-view-content");
  const urlBar = document.getElementById("browser-url-bar");
  const userBadge = document.getElementById("vp-user-badge");
  if (!contentEl) return;

  if (scenarioName === "honeypot") {
    if (urlBar) urlBar.textContent = "https://portal.northstar.edu/replica/admin-decoy";
    if (userBadge) userBadge.textContent = "Decoy Gateway (Trap Armed)";
    contentEl.innerHTML = `
      <div style="max-width: 500px; margin: 0 auto; width: 100%; display: flex; flex-direction: column; gap: 10px;">
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
          <!-- Decoy Admin Gateway Header -->
          <div style="background: #0f172a; color: #ffffff; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #b91c1c;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div style="width: 28px; height: 28px; border-radius: 4px; background: #fee2e2; display: flex; align-items: center; justify-content: center; color: #b91c1c; flex-shrink: 0;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              </div>
              <div>
                <div style="font-size: 0.9rem; font-weight: 700; letter-spacing: -0.01em;">Northstar University &bull; Infrastructure Management</div>
                <div style="font-size: 0.7rem; color: #94a3b8; font-family: var(--font-mono);">Internal Diagnostics Gateway &bull; /replica/admin-decoy</div>
              </div>
            </div>
            <span style="background: #7f1d1d; color: #fecaca; border: 1px solid #991b1b; padding: 2px 7px; border-radius: 3px; font-size: 0.66rem; font-weight: 700;">DECOY TRAP</span>
          </div>

          <!-- Decoy Warning Banner & Privacy Guarantee -->
          <div style="padding: 10px 14px; background: #fff1f2; border-bottom: 1px solid #fecdd3; font-size: 0.73rem; color: #9f1239; line-height: 1.45;">
            <strong>RESTRICTED ACCESS WARNING:</strong> This diagnostic interface is an automated defensive decoy trap. All probe interactions, scanning signatures, and unauthorized requests generate high-confidence security telemetry for automated source blocking.<br>
            <span style="display: block; margin-top: 4px; color: #475569; font-size: 0.7rem;">
              <strong>Strict Privacy Safeguard:</strong> The decoy trap records security event metadata only (source IP, timestamp, HTTP method, route). Submitted passwords, credentials, or request bodies are never saved or stored.
            </span>
          </div>

          <!-- Interactive Decoy Form -->
          <div style="padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; background: #ffffff;">
            <div>
              <label for="vp-decoy-subsystem" style="display: block; font-size: 0.72rem; font-weight: 600; color: #334155; margin-bottom: 4px;">Target Core Subsystem:</label>
              <select id="vp-decoy-subsystem" style="width: 100%; padding: 6px 10px; font-size: 0.76rem; border: 1px solid #cbd5e1; border-radius: 4px; background: #ffffff; color: #0f172a;">
                <option value="db_cluster">PostgreSQL Campus Records Database Pool (port 5432)</option>
                <option value="radius_aaa">RADIUS AAA Authentication &amp; 802.1X Gateway</option>
                <option value="core_bgp">Campus Core BGP / OSPF Routing Engine</option>
                <option value="ldap_auth">Active Directory / LDAP Credential Store</option>
              </select>
            </div>

            <div>
              <label for="vp-decoy-token" style="display: block; font-size: 0.72rem; font-weight: 600; color: #334155; margin-bottom: 4px;">Internal Maintenance Authorization Passphrase:</label>
              <input type="text" id="vp-decoy-token" value="DecoyProbeAttempt2026!" style="width: 100%; padding: 6px 10px; font-size: 0.76rem; font-family: var(--font-mono); border: 1px solid #cbd5e1; border-radius: 4px; background: #ffffff; color: #0f172a; box-sizing: border-box;">
            </div>

            <div style="display: flex; gap: 8px; align-items: center; margin-top: 4px;">
              <button id="vp-btn-trigger-decoy" style="width: 100%; padding: 8px 14px; font-size: 0.76rem; font-weight: 600; background: #dc2626; color: #ffffff; border: none; border-radius: 4px; cursor: pointer; transition: background 0.15s;">
                Initiate Core Diagnostic Dump &rarr;
              </button>
            </div>
          </div>

          <!-- Decoy Footer Strip -->
          <div style="padding: 7px 14px; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-between; font-size: 0.67rem; color: #64748b; font-family: var(--font-mono);">
            <span>Target: /replica/admin-decoy</span>
            <span>Simulated Scout: 198.51.100.88</span>
            <span>Fictional Replica</span>
          </div>
        </div>
      </div>
    `;
    const btnDecoy = document.getElementById("vp-btn-trigger-decoy");
    if (btnDecoy) {
      btnDecoy.addEventListener("click", () => handleStartScenario());
    }
  } else if (scenarioName === "benign_burst") {
    if (urlBar) urlBar.textContent = "https://portal.northstar.edu/replica/portal";
    if (userBadge) userBadge.textContent = "Elena Vance (#NS-88412)";
    const curBal = localStorage.getItem("nu_onecard_bal") || "420.50";
    contentEl.innerHTML = `
      <div style="max-width: 500px; margin: 0 auto; width: 100%; display: flex; flex-direction: column; gap: 10px;">
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="font-size: 0.92rem; font-weight: 700; color: #0f172a;">Elena Vance</div>
            <div style="font-size: 0.74rem; color: #64748b;">B.S. in Computer Science &bull; Academic Year 3</div>
          </div>
          <span style="background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; padding: 2px 7px; border-radius: 3px; font-size: 0.7rem; font-weight: 600;">Good Standing</span>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
          <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 10px;">
            <div style="font-size: 0.68rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Active Enrollment</div>
            <div style="font-size: 0.8rem; font-weight: 600; color: #0f172a; margin-top: 2px;">CS-302 (Distributed Systems)</div>
            <div style="font-size: 0.72rem; color: #64748b;">MATH-210 (Linear Algebra)</div>
          </div>
          <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 10px;">
            <div style="font-size: 0.68rem; color: #64748b; font-weight: 600; text-transform: uppercase;">OneCard Balance</div>
            <div style="font-size: 0.84rem; font-weight: 700; color: #15803d; margin-top: 2px;" id="vp-onecard-bal">$${curBal} Available</div>
            <div style="font-size: 0.72rem; color: #64748b;">Tuition: Settled (Fall '26)</div>
          </div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <button id="vp-btn-add-funds" style="padding: 5px 12px; font-size: 0.72rem; font-weight: 600; background: #15803d; color: #ffffff; border: none; border-radius: 4px; cursor: pointer;">+ Add $25 Funds</button>
          <a href="/replica/portal" target="_blank" style="padding: 5px 12px; font-size: 0.72rem; background: #ffffff; border: 1px solid #cbd5e1; color: #334155; text-decoration: none; border-radius: 4px;">Open Full Portal &rarr;</a>
        </div>
        <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 4px; padding: 6px 10px; font-size: 0.72rem; color: #1e40af; line-height: 1.35;">
          <strong>Registrar Notice:</strong> Priority course registration for the upcoming Spring term opens Monday at 08:00 EST.
        </div>
      </div>
    `;
    const btnAddFunds = document.getElementById("vp-btn-add-funds");
    if (btnAddFunds) {
      btnAddFunds.addEventListener("click", () => {
        const cur = parseFloat(localStorage.getItem("nu_onecard_bal") || "420.50");
        const next = cur + 25.0;
        localStorage.setItem("nu_onecard_bal", next.toFixed(2));
        const balEl = document.getElementById("vp-onecard-bal");
        if (balEl) balEl.textContent = "$" + next.toFixed(2) + " Available";
      });
    }
  } else {
    // Default: Slow-Rate Brute Force
    if (urlBar) urlBar.textContent = "https://portal.northstar.edu/replica/login";
    if (userBadge) userBadge.textContent = "Unauthenticated";
    contentEl.innerHTML = `
      <div style="max-width: 400px; margin: 0 auto; width: 100%; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">
          <div style="width: 32px; height: 32px; border-radius: 6px; background: #e0f2fe; display: flex; align-items: center; justify-content: center; color: #0284c7; flex-shrink: 0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          </div>
          <div>
            <div style="font-size: 0.94rem; font-weight: 700; color: #0f172a;">Central Authentication Service</div>
            <div style="font-size: 0.72rem; color: #64748b;">Northstar Single Sign-On (CAS)</div>
          </div>
        </div>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <div>
            <label style="display: block; font-size: 0.7rem; font-weight: 600; color: #475569; margin-bottom: 3px;">Northstar NetID</label>
            <input type="text" id="vp-login-user" value="admin" style="width: 100%; padding: 6px 10px; font-size: 0.75rem; border: 1px solid #cbd5e1; border-radius: 4px; background: #ffffff; color: #1e293b; font-family: var(--font-mono); box-sizing: border-box;">
          </div>
          <div>
            <label style="display: block; font-size: 0.7rem; font-weight: 600; color: #475569; margin-bottom: 3px;">Password</label>
            <input type="password" id="vp-login-pass" value="ReplicaLab2026!" style="width: 100%; padding: 6px 10px; font-size: 0.75rem; border: 1px solid #cbd5e1; border-radius: 4px; background: #ffffff; color: #1e293b; box-sizing: border-box;">
          </div>
          <div style="display: flex; gap: 8px; margin-top: 4px;">
            <button id="vp-btn-login-submit" style="flex: 1; padding: 7px 12px; font-size: 0.75rem; font-weight: 600; background: #0284c7; color: #ffffff; border: none; border-radius: 4px; cursor: pointer;">Sign In</button>
            <button id="vp-btn-trigger-spray" style="padding: 7px 12px; font-size: 0.75rem; font-weight: 600; background: #dc2626; color: #ffffff; border: none; border-radius: 4px; cursor: pointer;" title="Simulate Brute Force Attack">Run Spray Attack &rarr;</button>
          </div>
          <div id="vp-login-toast" style="display: none; padding: 6px 8px; border-radius: 4px; font-size: 0.72rem; margin-top: 4px;"></div>
        </div>
        <div style="font-size: 0.68rem; color: #64748b; text-align: center; margin-top: 10px; border-top: 1px solid #f1f5f9; padding-top: 8px;">
          Secured by Northstar Central Identity Management
        </div>
      </div>
    `;
    const btnSpray = document.getElementById("vp-btn-trigger-spray");
    if (btnSpray) {
      btnSpray.addEventListener("click", () => handleStartScenario());
    }
    const btnLogin = document.getElementById("vp-btn-login-submit");
    if (btnLogin) {
      btnLogin.addEventListener("click", async () => {
        const u = document.getElementById("vp-login-user").value;
        const p = document.getElementById("vp-login-pass").value;
        const toast = document.getElementById("vp-login-toast");
        try {
          const resp = await fetch("/replica/login", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify({ username: u, password: p }),
          });
          const res = await resp.json();
          toast.style.display = "block";
          if (resp.status === 200) {
            toast.style.background = "#dcfce7";
            toast.style.color = "#15803d";
            toast.textContent = "Authenticated as " + res.user + ". Session valid.";
          } else if (resp.status === 403) {
            toast.style.background = "#fee2e2";
            toast.style.color = "#b91c1c";
            toast.textContent = "Access Blocked: HTTP 403 by Mode 2 Guard.";
          } else {
            toast.style.background = "#fef3c7";
            toast.style.color = "#b45309";
            toast.textContent = "Authentication failed: Invalid credentials.";
          }
        } catch (e) {
          toast.style.display = "block";
          toast.style.background = "#fee2e2";
          toast.style.color = "#b91c1c";
          toast.textContent = "Error: " + e.message;
        }
      });
    }
  }
}

function clearAllTimers() {
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
  stepTimeouts.forEach(t => clearTimeout(t));
  stepTimeouts = [];
}

function resetStagesToPending() {
  updateStepTitles(currentScenario);
  const card1 = document.getElementById("step-detect-card");
  const card2 = document.getElementById("step-evidence-card");
  const card3 = document.getElementById("step-block-card");
  if (card1) card1.className = "progress-step-card";
  if (card2) card2.className = "progress-step-card";
  if (card3) card3.className = "progress-step-card";

  const s1 = document.getElementById("stage1-status");
  const s2 = document.getElementById("stage2-status");
  const s3 = document.getElementById("stage3-status");
  if (s1) s1.textContent = "PENDING";
  if (s2) s2.textContent = "PENDING";
  if (s3) s3.textContent = "PENDING";

  const decBadge = document.getElementById("decision-status-badge");
  if (decBadge) {
    decBadge.textContent = "READY";
    decBadge.className = "badge badge-low";
  }

  // Clear technical details stats
  const setEl = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };
  setEl("val-pps", "--");
  setEl("val-bps", "--");
  setEl("val-dur", "--");
  setEl("val-src-ip", "--");
  setEl("val-prod-score", "--");
  setEl("val-family", "--");
  setEl("val-policy-rule", "--");
  setEl("val-action", "--");
  setEl("val-reason", "--");

  const evEl = document.getElementById("val-evidence-list");
  if (evEl) evEl.innerHTML = '<span style="color: #64748b;">Awaiting scenario execution...</span>';
}

function updateButtonStates() {
  const btnStart = document.getElementById("btn-start");
  const btnPause = document.getElementById("btn-pause");
  if (!btnStart || !btnPause) return;

  if (isRunning) {
    btnStart.textContent = "Running...";
    btnStart.disabled = true;
    btnStart.style.opacity = "0.7";
    btnPause.disabled = false;
    btnPause.textContent = isPaused ? "Resume" : "Pause";
  } else {
    btnStart.textContent = "Run Scenario";
    btnStart.disabled = false;
    btnStart.style.opacity = "1";
    btnPause.disabled = true;
    btnPause.textContent = "Pause";
  }
}

async function loadScenarioComparison(scenName) {
  try {
    const res = await fetch(`/api/v1/replica/scenarios/comparison?scenario_name=${encodeURIComponent(scenName)}`);
    if (!res.ok) return;
    const data = await res.json();
    renderComparisonData(data);
  } catch (err) {
    console.error("Failed to load scenario comparison:", err);
  }
}

function renderComparisonData(data) {
  const loc = data.attack_location || {};
  const prot = data.protected_outcome || {};
  const hypo = data.counterfactual_outcome || {};

  // Update Attack Location Metadata Row
  const locSite = document.getElementById("loc-site");
  const locRoute = document.getElementById("loc-route");
  const locIp = document.getElementById("loc-ip");
  const locTime = document.getElementById("loc-time");

  if (locSite) locSite.textContent = loc.site_name || "Northstar Campus Portal (Lab Replica)";
  if (locRoute) locRoute.textContent = loc.target_route || "/replica/login";
  if (locIp) locIp.textContent = loc.simulated_source_ip || "198.51.100.77";
  if (locTime) {
    locTime.textContent = loc.timestamp ? new Date(loc.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
  }

  // Update Browser URL bar
  const urlBar = document.getElementById("browser-url-bar");
  if (urlBar) {
    urlBar.textContent = `https://portal.northstar.edu${loc.target_route || '/replica/login'}`;
  }

  // Update Progress Pipeline Steps
  updateStepTitles(currentScenario);
  const card1 = document.getElementById("step-detect-card");
  const card2 = document.getElementById("step-evidence-card");
  const card3 = document.getElementById("step-block-card");
  const s1 = document.getElementById("stage1-status");
  const s2 = document.getElementById("stage2-status");
  const s3 = document.getElementById("stage3-status");

  // Comparison section badges
  const protBadge = document.getElementById("comp-prot-badge");
  const protStatus = document.getElementById("comp-prot-status");
  const protImpact = document.getElementById("comp-prot-impact");
  const protGuidance = document.getElementById("comp-prot-guidance");

  if (prot.label === "BLOCK ACTIVE" && prot.http_status === 403) {
    if (card1) card1.className = "progress-step-card active-step";
    if (card2) card2.className = "progress-step-card active-step";
    if (card3) card3.className = "progress-step-card active-step";
    if (s1) s1.textContent = currentScenario === "honeypot" ? "ACCESSED" : "DETECTED";
    if (s2) s2.textContent = "CONFIRMED";
    if (s3) s3.textContent = "ACTIVE";

    if (protBadge) {
      protBadge.textContent = "BLOCK ACTIVE";
      protBadge.className = "badge-block-active-red";
    }
    if (protStatus) {
      protStatus.textContent = "HTTP 403 Forbidden (Block Active)";
      protStatus.style.color = "#ef4444";
    }

    showResultCard(currentScenario, { ...data, ...prot }, prot.ttl_remaining_seconds || 15, prot.expires_at);

  } else if (prot.status === "ALLOWLISTED_BYPASS" || prot.label === "ALLOWLISTED_BYPASS") {
    if (card1) card1.className = "progress-step-card success-step";
    if (card2) card2.className = "progress-step-card success-step";
    if (card3) card3.className = "progress-step-card success-step";
    if (s1) s1.textContent = "EVALUATED";
    if (s2) s2.textContent = "ALLOWLIST MATCHED";
    if (s3) s3.textContent = "ALLOWLISTED BYPASS";

    if (protBadge) {
      protBadge.textContent = "ALLOWLISTED BYPASS";
      protBadge.className = "badge-allowlisted";
    }
    if (protStatus) {
      protStatus.textContent = "HTTP 200 OK (Trusted Client Permitted)";
      protStatus.style.color = "#38bdf8";
    }

    // If overlay is already open (e.g., following manual run), keep content synchronized
    const overlay = document.getElementById("interception-overlay");
    if (overlay && overlay.style.display === "flex") {
      showResultCard(currentScenario, { ...data, ...prot }, 0, null);
    }

  } else {
    // READY — no block active
    if (card1) card1.className = "progress-step-card";
    if (card2) card2.className = "progress-step-card";
    if (card3) card3.className = "progress-step-card";
    if (s1) s1.textContent = "PENDING";
    if (s2) s2.textContent = "PENDING";
    if (s3) s3.textContent = "READY";

    if (protBadge) {
      protBadge.textContent = "READY — no block active";
      protBadge.className = "badge-ready";
    }
    if (protStatus) {
      protStatus.textContent = "HTTP 200 OK (No Block Active)";
      protStatus.style.color = "#94a3b8";
    }

    hideInterceptionOverlay();
  }

  if (protImpact) {
    protImpact.textContent = prot.business_impact || prot.reason || "--";
  }

  if (protGuidance) {
    if (prot.requires_scenario_run) {
      protGuidance.innerHTML = "<strong>Scenario must be run first:</strong> Click <code>Run Scenario</code> above to trigger detection and activate an ephemeral block.";
      protGuidance.style.display = "block";
    } else if (prot.label === "BLOCK ACTIVE") {
      protGuidance.innerHTML = `<strong>Active Block Confirmed:</strong> Local replica is actively dropping requests from <code>${loc.simulated_source_ip || ''}</code> (HTTP 403 Forbidden).`;
      protGuidance.style.display = "block";
    } else if (prot.status === "ALLOWLISTED_BYPASS" || prot.label === "ALLOWLISTED_BYPASS") {
      protGuidance.innerHTML = `<strong>Allowlist Bypass Confirmed:</strong> Client <code>${loc.simulated_source_ip || ''}</code> is on the trusted allowlist; traffic is permitted without blocking.`;
      protGuidance.style.display = "block";
    } else {
      protGuidance.style.display = "none";
    }
  }

  const hypoStatus = document.getElementById("comp-hypo-status");
  const hypoPage = document.getElementById("comp-hypo-page");
  const hypoImpact = document.getElementById("comp-hypo-impact");

  if (hypoStatus) {
    hypoStatus.textContent = `HTTP ${hypo.http_status} ${hypo.http_status === 200 ? 'OK (Compromised)' : 'Rate Limited'}`;
  }
  if (hypoPage) {
    hypoPage.textContent = hypo.hypothetical_page || "Simulated unauthorized access";
  }
  if (hypoImpact) {
    hypoImpact.textContent = hypo.business_impact || "--";
  }
}

function showResultCard(scenarioName, data, ttl, expiresAt) {
  const overlay = document.getElementById("interception-overlay");
  const card = document.getElementById("mode2-status-card");
  const iconWrap = document.getElementById("status-card-icon-wrap");
  const heading = document.getElementById("status-card-heading");
  const badge = document.getElementById("status-card-badge");
  const attackTypeEl = document.getElementById("res-attack-type");
  const whatHappenedEl = document.getElementById("res-what-happened");
  const evidenceEl = document.getElementById("res-evidence");
  const responseEl = document.getElementById("res-response");
  const privacyNoteEl = document.getElementById("res-honeypot-privacy");
  const expiryBox = document.getElementById("status-expiry-box");
  const ttlEl = document.getElementById("interception-ttl");
  const progressFill = document.getElementById("ttl-progress-fill");
  const mechEl = document.getElementById("res-enforcement-mech");

  if (!overlay) return;

  const isBlocked = !!(data && (data.action === "BLOCK" || data.replica_is_blocked || data.is_real_replica_enforced || data.label === "BLOCK ACTIVE" || data.status === "REPLICA_BLOCKED"));

  const eventBox = document.getElementById("res-honeypot-event-box");
  const honeyIdEl = document.getElementById("res-honey-id");
  const honeyRouteEl = document.getElementById("res-honey-route");
  const honeyMethodEl = document.getElementById("res-honey-method");
  const honeySrcEl = document.getElementById("res-honey-src");
  const honeyTsEl = document.getElementById("res-honey-ts");

  // 1. Attack Type
  if (attackTypeEl) {
    if (scenarioName === "bruteforce") {
      attackTypeEl.textContent = "Slow-Rate Credential Spray (BruteForce)";
    } else if (scenarioName === "honeypot") {
      attackTypeEl.textContent = "Honeypot probe — /replica/admin-decoy";
    } else if (scenarioName === "benign_burst") {
      attackTypeEl.textContent = "Authorized Administrative Burst (NormalTraffic)";
    } else {
      attackTypeEl.textContent = scenarioName || "--";
    }
  }

  // 2. What Happened
  if (whatHappenedEl) {
    if (scenarioName === "bruteforce") {
      whatHappenedEl.textContent = "Repeated failed logins targeted /replica/login, exceeding the threshold of 5 attempts.";
    } else if (scenarioName === "honeypot") {
      whatHappenedEl.textContent = "Simulated reconnaissance probe touched the hidden administrative decoy route /replica/admin-decoy.";
    } else if (scenarioName === "benign_burst") {
      whatHappenedEl.textContent = "Rapid maintenance burst from trusted admin client 10.0.0.99 against /replica/portal.";
    } else {
      whatHappenedEl.textContent = (data && (data.description || data.reason)) || "--";
    }
  }

  // 3. Evidence
  if (evidenceEl) {
    if (scenarioName === "bruteforce") {
      evidenceEl.textContent = "auth_failures: CONFIRMED (7 failures >= threshold 5)";
    } else if (scenarioName === "honeypot") {
      const evtId = (data && data.honeypot_event && data.honeypot_event.event_id) ? ` [${data.honeypot_event.event_id}]` : "";
      evidenceEl.textContent = `honeypot_interaction: CONFIRMED${evtId} — Decoy trap interaction confirmed on '/replica/admin-decoy'`;
    } else if (scenarioName === "benign_burst") {
      evidenceEl.textContent = "auth_failures: 0 (Unconfirmed), allowlist_check: MATCHED (10.0.0.99)";
    } else {
      evidenceEl.textContent = (data && Array.isArray(data.evidence_summary)) ? data.evidence_summary.join("; ") : "--";
    }
  }

  // 4. How SentinelX Responded
  if (responseEl) {
    if (isBlocked) {
      if (scenarioName === "bruteforce") {
        responseEl.textContent = "Temporarily blocked simulated source 198.51.100.77 in local replica for 15s. Subsequent requests receive HTTP 403 Forbidden.";
      } else if (scenarioName === "honeypot") {
        responseEl.textContent = "Temporarily blocked simulated scout 198.51.100.88 in local replica for 15s. Subsequent requests receive HTTP 403 Forbidden.";
      } else {
        responseEl.textContent = "Temporarily blocked simulated source in local replica for 15s. Subsequent requests receive HTTP 403 Forbidden.";
      }
    } else {
      responseEl.textContent = "Trusted client IP is on the lab allowlist; automated blocking bypassed with zero disruption to campus operations.";
    }
  }

  // 5. Honeypot Decoy Metadata Details
  if (scenarioName === "honeypot") {
    if (eventBox) eventBox.style.display = "block";
    const evt = (data && (data.honeypot_event || data.event)) || {};
    if (honeyIdEl) honeyIdEl.textContent = evt.event_id || (data && data.event_id) || "honey-scout-6191";
    if (honeyRouteEl) honeyRouteEl.textContent = evt.route || "/replica/admin-decoy";
    if (honeyMethodEl) honeyMethodEl.textContent = evt.http_method || "POST";
    if (honeySrcEl) honeySrcEl.textContent = evt.source_identity || "198.51.100.88";
    if (honeyTsEl) honeyTsEl.textContent = evt.timestamp ? new Date(evt.timestamp).toUTCString() : new Date().toUTCString();
  } else {
    if (eventBox) eventBox.style.display = "none";
  }

  // 6. Honeypot Privacy Assurance: Decoy records security event metadata only; passwords/bodies never stored
  if (privacyNoteEl) {
    if (scenarioName === "honeypot") {
      privacyNoteEl.style.display = "block";
      privacyNoteEl.innerHTML = "<strong>Strict Privacy Safeguard:</strong> The decoy trap records security event metadata only (source IP, timestamp, HTTP method, route). It does <em>not</em> save submitted passwords, credentials, or request bodies.";
    } else {
      privacyNoteEl.style.display = "none";
    }
  }

  // Visual appearance
  if (isBlocked) {
    if (card) card.className = "centered-status-card";
    if (heading) {
      heading.textContent = "Attack blocked — HTTP 403";
      heading.style.color = "#ef4444";
    }
    if (badge) {
      badge.textContent = "BLOCK ACTIVE";
      badge.className = "badge-block-active-red";
    }
    if (iconWrap) {
      iconWrap.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
    }
    if (expiryBox) expiryBox.style.display = "flex";
    if (mechEl) mechEl.textContent = "Enforced in-process by LocalReplicaAdapter";

    // Mode 2 local replica countdown (15s baseline)
    initialTtl = 15;
    if (expiresAt) {
      const now = Date.now();
      const exp = new Date(expiresAt).getTime();
      const rem = Math.max(0, Math.ceil((exp - now) / 1000));
      currentTtl = rem > 0 ? rem : (ttl || 15);
    } else {
      currentTtl = (ttl && ttl > 0) ? ttl : 15;
    }

    if (ttlEl) ttlEl.textContent = currentTtl;
    if (progressFill) {
      const pct = Math.max(0, Math.min(100, (currentTtl / initialTtl) * 100));
      progressFill.style.width = pct + "%";
    }

    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = setInterval(() => {
      if (isPaused) return;

      if (expiresAt) {
        currentTtl = Math.max(0, Math.ceil((new Date(expiresAt).getTime() - Date.now()) / 1000));
      } else {
        currentTtl -= 1;
      }

      if (ttlEl) ttlEl.textContent = Math.max(0, currentTtl);
      if (progressFill) {
        const pct = Math.max(0, Math.min(100, (currentTtl / initialTtl) * 100));
        progressFill.style.width = pct + "%";
      }

      if (currentTtl <= 0) {
        clearInterval(countdownTimer);
        countdownTimer = null;
        hideInterceptionOverlay();
        const statusBadge = document.getElementById("decision-status-badge");
        if (statusBadge) {
          statusBadge.textContent = "BLOCK EXPIRED (RESTORED)";
          statusBadge.className = "badge badge-low";
        }
        loadScenarioComparison(currentScenario);
      }
    }, 1000);

  } else {
    // Allowlisted bypass state
    if (card) card.className = "centered-status-card status-card-allowed";
    if (heading) {
      heading.textContent = "Request allowed — HTTP 200";
      heading.style.color = "#38bdf8";
    }
    if (badge) {
      badge.textContent = "ALLOWLISTED BYPASS";
      badge.className = "badge-allowlisted-card";
    }
    if (iconWrap) {
      iconWrap.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>';
    }
    if (expiryBox) expiryBox.style.display = "none";
    if (mechEl) mechEl.textContent = "Evaluated by LocalReplicaAdapter (Trusted Allowlist Bypass)";

    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  }

  overlay.style.display = "flex";
}

function showInterceptionOverlay(reason, ttl, expiresAt) {
  showResultCard(currentScenario, { reason: reason }, ttl, expiresAt);
}

function hideInterceptionOverlay() {
  const overlay = document.getElementById("interception-overlay");
  if (overlay) overlay.style.display = "none";
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
}

async function handleStartScenario() {
  if (isRunning) return;
  isRunning = true;
  isPaused = false;
  updateButtonStates();
  clearAllTimers();
  resetStagesToPending();
  hideInterceptionOverlay();
  updateViewportContent(currentScenario);

  const decBadge = document.getElementById("decision-status-badge");
  if (decBadge) {
    decBadge.textContent = "ANALYZING...";
    decBadge.className = "badge badge-medium";
  }

  const card1 = document.getElementById("step-detect-card");
  const card2 = document.getElementById("step-evidence-card");
  const card3 = document.getElementById("step-block-card");
  const s1 = document.getElementById("stage1-status");
  const s2 = document.getElementById("stage2-status");
  const s3 = document.getElementById("stage3-status");

  // Step 1: Flow Ingestion (200ms)
  stepTimeouts.push(setTimeout(() => {
    if (!isRunning || isPaused) return;
    if (card1) card1.className = "progress-step-card active-step";
    if (s1) {
      s1.textContent = currentScenario === "honeypot" ? "ACCESSED" : (currentScenario === "benign_burst" ? "EVALUATED" : "DETECTED");
    }

    if (currentScenario === "bruteforce") {
      document.getElementById("val-pps").textContent = "2.8 pkts/s";
      document.getElementById("val-bps").textContent = "420 B/s";
      document.getElementById("val-dur").textContent = "15.0 s";
      document.getElementById("val-src-ip").textContent = "198.51.100.77";
    } else if (currentScenario === "honeypot") {
      document.getElementById("val-pps").textContent = "16.6 pkts/s";
      document.getElementById("val-bps").textContent = "310 B/s";
      document.getElementById("val-dur").textContent = "1.2 s";
      document.getElementById("val-src-ip").textContent = "198.51.100.88";

      const locSite = document.getElementById("loc-site");
      const locRoute = document.getElementById("loc-route");
      const locIp = document.getElementById("loc-ip");
      const locTime = document.getElementById("loc-time");
      if (locSite) locSite.textContent = "Northstar Campus Portal (Lab Replica)";
      if (locRoute) locRoute.textContent = "/replica/admin-decoy";
      if (locIp) locIp.textContent = "198.51.100.88";
      if (locTime) locTime.textContent = new Date().toLocaleTimeString();
    } else {
      document.getElementById("val-pps").textContent = "82.5 pkts/s";
      document.getElementById("val-bps").textContent = "450 kB/s";
      document.getElementById("val-dur").textContent = "2.0 s";
      document.getElementById("val-src-ip").textContent = "10.0.0.99 (Admin)";
    }
  }, 200));

  // Step 2: Scoring & Evidence Correlation (600ms)
  stepTimeouts.push(setTimeout(() => {
    if (!isRunning || isPaused) return;
    if (card2) card2.className = "progress-step-card active-step";
    if (s2) s2.textContent = "CONFIRMED";

    const scoreEl = document.getElementById("val-prod-score");
    const famEl = document.getElementById("val-family");
    const actEl = document.getElementById("val-activation");
    const evEl = document.getElementById("val-evidence-list");

    if (currentScenario === "bruteforce") {
      if (scoreEl) { scoreEl.textContent = "1.000"; scoreEl.style.color = "#ef4444"; }
      if (famEl) famEl.textContent = "BruteForce";
      if (actEl) actEl.textContent = "0.56 (ACTIVE)";
      if (evEl) {
        evEl.innerHTML = `
          <div>&bull; <strong>auth_failures:</strong> <span style="color: #ef4444; font-weight: 700;">CONFIRMED (7 failures &ge; 5)</span></div>
          <div>&bull; <strong>waf_event:</strong> <span style="color: #94a3b8;">UNCONFIRMED</span></div>
          <div>&bull; <strong>evidence_state:</strong> <span style="color: #10b981; font-weight: 600;">CONFIRMED</span></div>
        `;
      }
    } else if (currentScenario === "honeypot") {
      if (scoreEl) { scoreEl.textContent = "0.900"; scoreEl.style.color = "#ef4444"; }
      if (famEl) famEl.textContent = "Probe/Recon";
      if (actEl) actEl.textContent = "0.56 (ACTIVE)";
      if (evEl) {
        evEl.innerHTML = `
          <div>&bull; <strong>honeypot_interaction:</strong> <span style="color: #ef4444; font-weight: 700;">CONFIRMED (/replica/admin-decoy)</span></div>
          <div>&bull; <strong>decoy_trap:</strong> <span style="color: #38bdf8;">Decoy route touched by 198.51.100.88</span></div>
          <div>&bull; <strong>privacy_guarantee:</strong> <span style="color: #10b981; font-weight: 600;">Security event metadata only (no passwords/bodies saved)</span></div>
        `;
      }
    } else {
      if (scoreEl) { scoreEl.textContent = "0.350"; scoreEl.style.color = "#10b981"; }
      if (famEl) famEl.textContent = "NormalTraffic";
      if (actEl) actEl.textContent = "0.56 (INACTIVE)";
      if (evEl) {
        evEl.innerHTML = `
          <div>&bull; <strong>auth_failures:</strong> <span style="color: #94a3b8;">UNCONFIRMED (0 failures)</span></div>
          <div>&bull; <strong>allowlist_check:</strong> <span style="color: #10b981; font-weight: 700;">MATCHED (10.0.0.99)</span></div>
          <div>&bull; <strong>evidence_state:</strong> <span style="color: #94a3b8;">BYPASSED</span></div>
        `;
      }
    }
  }, 600));

  // Step 3: Execute Scenario via Backend & Apply Ephemeral Defense (1200ms)
  stepTimeouts.push(setTimeout(async () => {
    if (!isRunning) return;

    try {
      const res = await fetch("/api/v1/replica/scenarios/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario_name: currentScenario }),
      });

      if (!res.ok) {
        throw new Error(`Scenario run failed with status ${res.status}`);
      }

      const runData = await res.json();
      
      const valRule = document.getElementById("val-policy-rule");
      const valAction = document.getElementById("val-action");
      const valReason = document.getElementById("val-reason");

      if (valRule) valRule.textContent = runData.policy_rule || "AUTHORIZED_INDEPENDENT_EVIDENCE";
      if (valAction) {
        valAction.textContent = runData.action || "BLOCK";
        valAction.style.color = runData.action === "BLOCK" ? "#ef4444" : "#10b981";
      }
      if (valReason) valReason.textContent = runData.reason || "--";

      if (runData.action === "BLOCK") {
        if (card3) card3.className = "progress-step-card active-step";
        if (s3) s3.textContent = "ACTIVE";
        if (decBadge) {
          decBadge.textContent = "DEFENSE ACTIVE: BLOCKED";
          decBadge.className = "badge badge-critical";
        }
        showResultCard(
          currentScenario,
          runData,
          runData.active_block?.ttl_seconds || 15,
          runData.active_block?.expires_at
        );
      } else {
        if (card1) card1.className = "progress-step-card success-step";
        if (card2) card2.className = "progress-step-card success-step";
        if (card3) card3.className = "progress-step-card success-step";
        if (s1) s1.textContent = "EVALUATED";
        if (s2) s2.textContent = "ALLOWLIST MATCHED";
        if (s3) s3.textContent = "ALLOWLISTED BYPASS";
        if (decBadge) {
          decBadge.textContent = "ALLOWLIST BYPASS (PERMITTED)";
          decBadge.className = "badge badge-low";
        }
        showResultCard(currentScenario, runData, 0, null);
      }

      // Refresh comparison data for updated countdown and timestamps
      await loadScenarioComparison(currentScenario);

    } catch (err) {
      console.error("Error executing replica scenario:", err);
      if (s3) s3.textContent = "ERROR";
      if (decBadge) decBadge.textContent = "ERROR";
    } finally {
      isRunning = false;
      updateButtonStates();
    }
  }, 1200));
}

function handlePauseScenario() {
  if (!isRunning && !countdownTimer) return;
  isPaused = !isPaused;
  const btnPause = document.getElementById("btn-pause");
  if (btnPause) {
    btnPause.textContent = isPaused ? "Resume" : "Pause";
    btnPause.className = isPaused ? "pres-btn pres-btn-start" : "pres-btn pres-btn-pause";
  }
}

async function handleResetScenario() {
  clearAllTimers();
  isRunning = false;
  isPaused = false;
  updateButtonStates();

  try {
    const res = await fetch("/api/v1/replica/scenarios/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });

    if (res.ok) {
      const data = await res.json();
      console.log("Scenario reset completed:", data);
    }
  } catch (err) {
    console.error("Failed to reset scenario:", err);
  }

  resetStagesToPending();
  hideInterceptionOverlay();
  updateViewportContent(currentScenario);
  await loadScenarioComparison(currentScenario);
}
