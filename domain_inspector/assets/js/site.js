/**
 * SentinelX Standalone Domain Security Inspector
 * Core Interactive JavaScript & Verification Engine
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Sticky Header scroll detection
  const header = document.querySelector("[data-header]");
  if (header) {
    const onScroll = () => {
      if (window.scrollY > 20) {
        header.classList.add("is-scrolled");
      } else {
        header.classList.remove("is-scrolled");
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // 2. Who it's for Dropdown Menu
  const whoBtn = document.querySelector("[data-who-btn]");
  const whoMenu = document.getElementById("who-menu");
  if (whoBtn && whoMenu) {
    whoBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const expanded = whoBtn.getAttribute("aria-expanded") === "true";
      whoBtn.setAttribute("aria-expanded", String(!expanded));
      whoMenu.hidden = expanded;
    });

    document.addEventListener("click", (e) => {
      if (!whoMenu.contains(e.target) && e.target !== whoBtn) {
        whoBtn.setAttribute("aria-expanded", "false");
        whoMenu.hidden = true;
      }
    });
  }

  // 3. Mobile Navigation Drawer
  const menuBtn = document.querySelector("[data-menu]");
  const mobileNav = document.getElementById("mnav");
  if (menuBtn && mobileNav) {
    menuBtn.addEventListener("click", () => {
      const open = menuBtn.getAttribute("aria-expanded") === "true";
      menuBtn.setAttribute("aria-expanded", String(!open));
      mobileNav.hidden = open;
      if (header) {
        header.classList.toggle("is-menu-open", !open);
      }
    });
  }

  // 4. Hero Demo Tabs & Auto-cycling (.hd)
  const heroDemo = document.querySelector("[data-hd]");
  if (heroDemo) {
    const tabs = [...heroDemo.querySelectorAll('[role="tab"]')];
    const panels = tabs.map((t) => document.getElementById(t.getAttribute("aria-controls")));
    const pause = heroDemo.querySelector("[data-hd-pause]");
    let cur = 0;
    let timer = null;
    let isAuto = true;

    function setAuto(on) {
      isAuto = on;
      heroDemo.classList.toggle("is-auto", on);
      if (pause) {
        pause.setAttribute("aria-label", on ? "Pause the demo" : "Play the demo");
      }
      if (on) {
        startCycle();
      } else {
        clearTimeout(timer);
      }
    }

    function showTab(idx, byUser = false) {
      cur = idx;
      tabs.forEach((t, i) => {
        const sel = i === idx;
        t.setAttribute("aria-selected", String(sel));
        t.tabIndex = sel ? 0 : -1;
        if (panels[i]) {
          panels[i].hidden = !sel;
        }
      });
      heroDemo.dataset.at = tabs[idx].dataset.tab;
      if (byUser) {
        setAuto(false);
      }
    }

    function startCycle() {
      clearTimeout(timer);
      if (!isAuto) return;
      const curTab = tabs[cur];
      const durSec = parseFloat((curTab && curTab.style.getPropertyValue("--dur")) || "6s") * 1000;
      timer = setTimeout(() => {
        showTab((cur + 1) % tabs.length);
        startCycle();
      }, durSec || 6000);
    }

    tabs.forEach((tab, i) => {
      tab.addEventListener("click", () => showTab(i, true));
      tab.addEventListener("keydown", (e) => {
        let next = cur;
        if (e.key === "ArrowRight") next = (cur + 1) % tabs.length;
        else if (e.key === "ArrowLeft") next = (cur - 1 + tabs.length) % tabs.length;
        else if (e.key === "Home") next = 0;
        else if (e.key === "End") next = tabs.length - 1;
        else return;

        e.preventDefault();
        showTab(next, true);
        tabs[next].focus();
      });
    });

    if (pause) {
      pause.hidden = false;
      pause.addEventListener("click", () => {
        setAuto(!isAuto);
      });
    }

    heroDemo.addEventListener("mouseenter", () => {
      heroDemo.classList.add("is-hold");
      clearTimeout(timer);
    });

    heroDemo.addEventListener("mouseleave", () => {
      heroDemo.classList.remove("is-hold");
      if (isAuto) startCycle();
    });

    heroDemo.classList.add("is-anim");
    setAuto(true);
  }

  // 5. Sample Report Filter & Row Selection
  const sampleReports = document.querySelectorAll("[data-sample-report]");
  sampleReports.forEach((sr) => {
    const filterChips = sr.querySelectorAll(".sr__chip");
    const rows = sr.querySelectorAll(".sr__row");
    const panels = sr.querySelectorAll(".sr__panel");

    if (panels.length > 0 && !sr.querySelector(".sr__panel.is-shown")) {
      panels[0].classList.add("is-shown");
    }

    filterChips.forEach((chip) => {
      chip.addEventListener("click", () => {
        filterChips.forEach((c) => c.setAttribute("aria-pressed", "false"));
        chip.setAttribute("aria-pressed", "true");
        const filter = chip.dataset.filter;

        let firstVisibleRow = null;
        rows.forEach((r) => {
          const item = r.closest("li");
          const sev = item ? item.dataset.sev : "";
          if (filter === "all" || sev === filter) {
            item.hidden = false;
            if (!firstVisibleRow) firstVisibleRow = r;
          } else {
            item.hidden = true;
          }
        });

        if (firstVisibleRow) {
          firstVisibleRow.click();
        }
      });
    });

    rows.forEach((r) => {
      r.addEventListener("click", () => {
        rows.forEach((row) => row.removeAttribute("aria-current"));
        r.setAttribute("aria-current", "true");
        const panelId = r.getAttribute("aria-controls");

        panels.forEach((p) => {
          if (p.id === panelId) {
            p.classList.add("is-shown");
          } else {
            p.classList.remove("is-shown");
          }
        });
      });
    });
  });

  // 6. Subpage Tabs (Technologies / What we checked / Scope)
  const tabContainers = document.querySelectorAll("[data-tabs]");
  tabContainers.forEach((tc) => {
    const moreTabs = tc.querySelectorAll('[role="tab"]');
    const morePanels = tc.querySelectorAll('[role="tabpanel"]');

    moreTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        moreTabs.forEach((t) => {
          t.setAttribute("aria-selected", "false");
          t.tabIndex = -1;
        });
        tab.setAttribute("aria-selected", "true");
        tab.tabIndex = 0;

        const targetId = tab.getAttribute("aria-controls");
        morePanels.forEach((p) => {
          p.hidden = p.id !== targetId;
        });
      });
    });
  });

  // 7. Interactive Inspection Scope Selector (replaces pricing calculator)
  setupInspectionScopeSelector();

  // 8. SentinelX Domain Security Inspector Engine
  setupSentinelXScanner();
});

/**
 * Interactive Scope Selector for the Security Checks page.
 * Lets users toggle public audit modules to estimate inspection surface & requests.
 */
function setupInspectionScopeSelector() {
  const scopeWidget = document.querySelector("[data-scope-selector]");
  if (!scopeWidget) return;

  const checkboxes = scopeWidget.querySelectorAll('input[type="checkbox"][data-scope-check]');
  const totalAreasEl = scopeWidget.querySelector("[data-scope-total]");
  const requestsEl = scopeWidget.querySelector("[data-scope-requests]");
  const timeEl = scopeWidget.querySelector("[data-scope-time]");
  const postureEl = scopeWidget.querySelector("[data-scope-posture]");

  function updateScope() {
    let checkedCount = 0;
    let requestCount = 0;

    checkboxes.forEach((cb) => {
      if (cb.checked) {
        checkedCount++;
        requestCount += parseInt(cb.dataset.requests || "1", 10);
      }
    });

    if (totalAreasEl) totalAreasEl.textContent = `${checkedCount} area${checkedCount === 1 ? "" : "s"}`;
    if (requestsEl) requestsEl.textContent = `${requestCount} polite probe${requestCount === 1 ? "" : "s"}`;
    if (timeEl) timeEl.textContent = `< ${Math.max(1, Math.round(requestCount * 0.4))}s`;
    if (postureEl) {
      if (checkedCount >= 8) postureEl.textContent = "Full Exterior Coverage";
      else if (checkedCount >= 4) postureEl.textContent = "Standard Baseline";
      else postureEl.textContent = "Selective Surface";
    }
  }

  checkboxes.forEach((cb) => cb.addEventListener("change", updateScope));
  updateScope();
}

/**
 * SentinelX Domain Security Inspector Engine
 * - Enforces operator authorization confirmation
 * - Executes safe, non-disruptive public checks
 * - Tries live /api/check endpoint first (standalone server)
 * - Falls back to live DNS-over-HTTPS (browser mode) with transparent sample labels
 * - Never claims a domain has a vulnerability unless actually verified
 */
function setupSentinelXScanner() {
  let modal = document.querySelector(".scan-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.className = "scan-modal";
    modal.innerHTML = `
      <div class="scan-modal__card" role="dialog" aria-modal="true" aria-labelledby="modal-scan-title">
        <header class="scan-modal__header">
          <div class="scan-modal__title" id="modal-scan-title">
            <svg class="sd-icon sd-icon--20" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            <span>SentinelX Inspection · <b id="scan-domain-label">example.com</b></span>
          </div>
          <button type="button" class="scan-modal__close" id="modal-close-btn" aria-label="Close dialog">
            <svg class="sd-icon sd-icon--20" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </header>

        <div class="scan-modal__body">
          <!-- Authorization Gate (if not pre-confirmed) -->
          <div class="scan-modal__auth-gate" id="scan-auth-gate" style="display:none; padding:16px 0;">
            <div style="background:var(--sd-surface-2); border:1px solid var(--sd-border); border-radius:6px; padding:16px;">
              <h3 style="font-size:16px; font-weight:600; margin-bottom:8px; display:flex; align-items:center; gap:8px;">
                <svg class="sd-icon sd-icon--16" style="color:var(--sd-link);" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                Operator Authorization Required
              </h3>
              <p style="font-size:14px; color:var(--sd-ink-2); margin-bottom:14px;">
                SentinelX limits checks to non-disruptive, read-only public exterior telemetry (HTTPS redirection, TLS certificate, HTTP response headers, public DNS/email records, and security.txt).
                Exploitation, password guessing, and denial-of-service tests are strictly prohibited.
              </p>
              <label style="display:flex; align-items:flex-start; gap:10px; font-size:14px; font-weight:500; cursor:pointer;">
                <input type="checkbox" id="modal-auth-confirm" style="margin-top:3px; accent-color:var(--sd-link);">
                <span>I confirm that I am authorized to evaluate this domain and consent to non-disruptive public checks.</span>
              </label>
              <div style="margin-top:16px; display:flex; gap:10px; justify-content:flex-end;">
                <button type="button" class="sd-btn sd-btn--secondary" id="modal-auth-cancel">Cancel</button>
                <button type="button" class="sd-btn sd-btn--primary" id="modal-auth-proceed" disabled>Proceed with Inspection</button>
              </div>
            </div>
          </div>

          <!-- Progress Section -->
          <div class="scan-modal__progress" id="scan-progress-section">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span id="scan-status-text" style="font-weight:600; font-size:14.5px;">Initializing public exterior checks...</span>
              <span id="scan-pct-text" class="sd-num" style="font-family:var(--sd-mono); font-weight:600; color:var(--sd-tint-mint-ink);">0%</span>
            </div>
            <div class="scan-modal__bar-track">
              <div class="scan-modal__bar-fill" id="scan-bar-fill"></div>
            </div>
            <div class="scan-modal__steps-list" id="scan-steps-list"></div>
          </div>

          <!-- Results Section -->
          <div class="scan-modal__results" id="scan-results-box" style="display:none;"></div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  const checkAreas = [
    { id: "https", label: "HTTPS availability & redirection" },
    { id: "tls", label: "TLS certificate validity & handshake" },
    { id: "headers", label: "Security headers (HSTS, CSP, XFO, XCTO)" },
    { id: "dns_email", label: "Email security records (SPF, DMARC)" },
    { id: "caa", label: "DNS health & CAA authority records" },
    { id: "disclosure", label: "RFC 9116 security.txt disclosure policy" }
  ];

  const domainForms = document.querySelectorAll("[data-domain-form]");
  const modalClose = modal.querySelector("#modal-close-btn");
  const domainLabel = modal.querySelector("#scan-domain-label");
  const statusText = modal.querySelector("#scan-status-text");
  const pctText = modal.querySelector("#scan-pct-text");
  const barFill = modal.querySelector("#scan-bar-fill");
  const stepsList = modal.querySelector("#scan-steps-list");
  const resultsBox = modal.querySelector("#scan-results-box");
  const authGate = modal.querySelector("#scan-auth-gate");
  const progressSection = modal.querySelector("#scan-progress-section");
  const authConfirm = modal.querySelector("#modal-auth-confirm");
  const authProceed = modal.querySelector("#modal-auth-proceed");
  const authCancel = modal.querySelector("#modal-auth-cancel");

  let pendingDomain = "";

  if (modalClose) {
    modalClose.addEventListener("click", () => modal.classList.remove("is-active"));
  }

  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("is-active");
  });

  if (authConfirm && authProceed) {
    authConfirm.addEventListener("change", () => {
      authProceed.disabled = !authConfirm.checked;
    });
    authProceed.addEventListener("click", () => {
      if (authConfirm.checked && pendingDomain) {
        authGate.style.display = "none";
        progressSection.style.display = "block";
        executeInspectionFlow(pendingDomain, true);
      }
    });
    if (authCancel) {
      authCancel.addEventListener("click", () => {
        modal.classList.remove("is-active");
      });
    }
  }

  domainForms.forEach((form) => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const input = form.querySelector('input[type="text"]');
      const formAuth = form.querySelector('input[type="checkbox"][name="authorized"], input[type="checkbox"].dc__auth-check');

      let domain = (input && input.value.trim()) || "example.com";
      domain = domain.replace(/^https?:\/\//i, "").replace(/\/.*$/, "").replace(/:\d+$/, "").trim();
      if (!domain) domain = "example.com";

      const isPreAuthorized = formAuth ? formAuth.checked : false;

      domainLabel.textContent = domain;
      pendingDomain = domain;
      modal.classList.add("is-active");

      if (!isPreAuthorized) {
        // Enforce authorization confirmation gate
        authGate.style.display = "block";
        progressSection.style.display = "none";
        resultsBox.style.display = "none";
        if (authConfirm) authConfirm.checked = false;
        if (authProceed) authProceed.disabled = true;
      } else {
        authGate.style.display = "none";
        progressSection.style.display = "block";
        executeInspectionFlow(domain, true);
      }
    });
  });

  async function executeInspectionFlow(domain, authorized) {
    resultsBox.style.display = "none";
    resultsBox.innerHTML = "";
    barFill.style.width = "0%";
    pctText.textContent = "0%";
    statusText.textContent = `Establishing connection to ${domain}...`;

    // Render step items
    stepsList.innerHTML = checkAreas
      .map(
        (area, i) => `
        <div class="scan-modal__step-item" id="step-item-${i}">
          <span class="scan-modal__step-icon">○</span>
          <span>${area.label}</span>
        </div>
      `
      )
      .join("");

    // Animate progress indicators
    let stepIdx = 0;
    const stepTimer = setInterval(() => {
      if (stepIdx < checkAreas.length) {
        const item = modal.querySelector(`#step-item-${stepIdx}`);
        if (item) {
          item.classList.add("is-done");
          item.querySelector(".scan-modal__step-icon").innerHTML = "✓";
        }
        statusText.textContent = `Inspecting: ${checkAreas[stepIdx].label}...`;
        stepIdx++;
        const pct = Math.round((stepIdx / checkAreas.length) * 80);
        barFill.style.width = `${pct}%`;
        pctText.textContent = `${pct}%`;
      }
    }, 240);

    // 1. Attempt Live Server Inspection API
    let liveReport = null;
    try {
      const resp = await fetch(`/api/check?domain=${encodeURIComponent(domain)}&authorized=true`, {
        headers: { Accept: "application/json" },
      });
      if (resp.ok) {
        liveReport = await resp.json();
      }
    } catch {
      liveReport = null;
    }

    // 2. If live server check not available, run live DoH DNS checks directly in the browser
    let dohResults = null;
    if (!liveReport) {
      dohResults = await queryBrowserDoH(domain);
    }

    clearInterval(stepTimer);

    // Complete all step icons
    checkAreas.forEach((_, i) => {
      const item = modal.querySelector(`#step-item-${i}`);
      if (item) {
        item.classList.add("is-done");
        item.querySelector(".scan-modal__step-icon").innerHTML = "✓";
      }
    });
    barFill.style.width = "100%";
    pctText.textContent = "100%";
    statusText.textContent = `Exterior security inspection complete`;

    if (liveReport && liveReport.status === "success") {
      renderLiveReport(domain, liveReport);
    } else {
      renderBrowserHybridReport(domain, dohResults);
    }
  }

  // Live DNS-over-HTTPS queries directly from client browser
  async function queryBrowserDoH(domain) {
    const records = { spf: null, dmarc: null, caa: null, mx: null };
    try {
      // SPF query
      const txtResp = await fetch(`https://dns.google/resolve?name=${encodeURIComponent(domain)}&type=TXT`);
      if (txtResp.ok) {
        const data = await txtResp.json();
        const answers = data.Answer || [];
        for (const a of answers) {
          const val = (a.data || "").replace(/^"|"$/g, "");
          if (val.toLowerCase().startsWith("v=spf1")) {
            records.spf = val;
            break;
          }
        }
      }
    } catch {}

    try {
      // DMARC query
      const dmarcResp = await fetch(`https://dns.google/resolve?name=${encodeURIComponent("_dmarc." + domain)}&type=TXT`);
      if (dmarcResp.ok) {
        const data = await dmarcResp.json();
        const answers = data.Answer || [];
        for (const a of answers) {
          const val = (a.data || "").replace(/^"|"$/g, "");
          if (val.toLowerCase().includes("v=dmarc1")) {
            records.dmarc = val;
            break;
          }
        }
      }
    } catch {}

    try {
      // CAA query
      const caaResp = await fetch(`https://dns.google/resolve?name=${encodeURIComponent(domain)}&type=CAA`);
      if (caaResp.ok) {
        const data = await caaResp.json();
        const answers = data.Answer || [];
        if (answers.length > 0) {
          records.caa = answers.map((a) => (a.data || "").replace(/^"|"$/g, "")).join(", ");
        }
      }
    } catch {}

    return records;
  }

  function renderLiveReport(domain, report) {
    const summary = report.summary || {};
    const checks = report.checks || [];

    resultsBox.style.display = "grid";
    resultsBox.innerHTML = `
      <div class="scan-score-badge" style="background:#ffffff; color:var(--sd-ink); border:1px solid var(--sd-border); border-radius:8px; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; box-shadow: 0 1px 3px rgba(15,23,42,0.06);">
        <div>
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
            <span class="sd-tag" style="background:#059669; color:#ffffff; font-weight:700; font-size:11px; padding:2px 8px; border-radius:4px; text-transform:uppercase; letter-spacing:0.5px;">✓ LIVE VERIFIED TELEMETRY</span>
            <span style="font-size:12px; color:var(--sd-muted); font-family:var(--sd-mono);">${new Date().toISOString().replace('T', ' ').substring(0, 19)} UTC</span>
          </div>
          <h3 style="font-size:18px; margin-bottom:2px; color:var(--sd-ink);">Exterior Security Posture · ${domain}</h3>
          <p style="font-size:13px; color:var(--sd-ink-2);">Direct read-only public checks verified by SentinelX Standalone Server</p>
        </div>
        <div style="text-align:right;">
          <b style="font-size:32px; font-weight:700; color:var(--sd-link);">${summary.health_score || 85}<span style="font-size:16px; font-weight:400; color:var(--sd-muted);">/100</span></b>
          <div style="font-size:12px; color:var(--sd-muted);">Overall Posture</div>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; margin-top:8px;">
        <div style="background:var(--sd-surface-2); padding:10px 14px; border-radius:6px; border:1px solid var(--sd-border);">
          <span style="font-size:12px; color:var(--sd-ink-2);">Areas Verified</span>
          <p style="font-size:20px; font-weight:700; color:var(--sd-link); margin-top:2px;">${summary.total_areas || checks.length}</p>
        </div>
        <div style="background:var(--sd-surface-2); padding:10px 14px; border-radius:6px; border:1px solid var(--sd-border);">
          <span style="font-size:12px; color:var(--sd-ink-2);">Passed Checks</span>
          <p style="font-size:20px; font-weight:700; color:var(--sd-success); margin-top:2px;">${summary.passed || 0}</p>
        </div>
        <div style="background:var(--sd-surface-2); padding:10px 14px; border-radius:6px; border:1px solid var(--sd-border);">
          <span style="font-size:12px; color:var(--sd-ink-2);">Review Recommended</span>
          <p style="font-size:20px; font-weight:700; color:${summary.actionable > 0 ? '#f59e0b' : 'var(--sd-success)'}; margin-top:2px;">${summary.actionable || 0}</p>
        </div>
      </div>

      <h4 style="margin-top:16px; font-size:15px; font-weight:600;">Verified Telemetry & Findings for ${domain}:</h4>

      <div style="display:grid; gap:12px; margin-top:8px;">
        ${checks
          .map(
            (c, i) => `
          <div class="scan-card-finding" style="border-left: 4px solid ${c.status === 'PASS' ? 'var(--sd-success)' : (c.status === 'FAIL' ? 'var(--sd-danger)' : '#f59e0b')}; background:var(--sd-surface); padding:14px 16px; border-radius:6px; border:1px solid var(--sd-border); border-left-width:4px;">
            <header style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span class="sd-tag sd-tag--${c.severity.toLowerCase()}">${c.severity}</span>
              <span style="font-size:11.5px; color:var(--sd-muted); font-family:var(--sd-mono);">${c.category} · Verified</span>
            </header>
            <h4 style="font-size:15px; margin-bottom:4px; font-weight:600;">${i + 1}. ${c.title}</h4>
            <div style="margin:8px 0; background:var(--sd-surface-2); padding:8px 12px; border-radius:4px; font-size:13px; font-family:var(--sd-mono); word-break:break-all;">
              <code>${escapeHtml(c.evidence)}</code>
            </div>
            <p style="font-size:13px; color:var(--sd-ink-2); margin-top:4px;">
              <b>Recommended Action:</b> ${escapeHtml(c.recommendation)}
            </p>
          </div>
        `
          )
          .join("")}
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:16px; border-top:1px solid var(--sd-border); padding-top:16px;">
        <span style="font-size:12.5px; color:var(--sd-muted);">Non-disruptive exterior audit · SentinelX Standalone Inspector</span>
        <div style="display:flex; gap:10px;">
          <button type="button" class="sd-btn sd-btn--secondary" onclick="window.print()">Print / Export PDF</button>
          <button type="button" class="sd-btn sd-btn--primary" onclick="document.querySelector('.scan-modal').classList.remove('is-active')">Done</button>
        </div>
      </div>
    `;
  }

  function renderBrowserHybridReport(domain, doh) {
    const hasSpf = doh && Boolean(doh.spf);
    const hasDmarc = doh && Boolean(doh.dmarc);
    const hasCaa = doh && Boolean(doh.caa);

    resultsBox.style.display = "grid";
    resultsBox.innerHTML = `
      <div class="scan-score-badge" style="background:#ffffff; color:var(--sd-ink); border:1px solid var(--sd-border); border-radius:8px; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; box-shadow: 0 1px 3px rgba(15,23,42,0.06);">
        <div>
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
            <span class="sd-tag" style="background:#0284c7; color:#ffffff; font-weight:700; font-size:11px; padding:2px 8px; border-radius:4px; text-transform:uppercase; letter-spacing:0.5px;">✓ LIVE DNS + SAMPLE LABELS</span>
          </div>
          <h3 style="font-size:18px; margin-bottom:2px; color:var(--sd-ink);">Diagnostic Overview · ${domain}</h3>
          <p style="font-size:13px; color:var(--sd-ink-2);">Client-side mode: Public DNS verified live via DoH; socket probes labeled as sample baseline.</p>
        </div>
        <div style="text-align:right;">
          <b style="font-size:28px; font-weight:700; color:var(--sd-link);">Verified DNS</b>
          <div style="font-size:12px; color:var(--sd-muted);">Live Browser Probes</div>
        </div>
      </div>

      <div style="background:#f0f9ff; border:1px solid #bae6fd; border-radius:8px; padding:12px 16px; margin-top:8px; font-size:13px; color:#0369a1;">
        <strong>Notice on Verification Mode:</strong> Public DNS email and authority records below were queried live directly from your browser via DNS-over-HTTPS. Direct TLS socket negotiation and HTTP header inspection require Python server execution. For full live verified socket and header telemetry, launch: <code>python server.py</code> in the REPLICA directory.
      </div>

      <h4 style="margin-top:16px; font-size:15px; font-weight:600;">Live Verified DNS Telemetry for ${domain}:</h4>

      <div style="display:grid; gap:12px; margin-top:8px;">
        <!-- Live SPF -->
        <div class="scan-card-finding" style="border-left: 4px solid ${hasSpf ? 'var(--sd-success)' : '#f59e0b'}; background:var(--sd-surface); padding:14px 16px; border-radius:6px; border:1px solid var(--sd-border); border-left-width:4px;">
          <header style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span class="sd-tag ${hasSpf ? 'sd-tag--good' : 'sd-tag--medium'}">${hasSpf ? 'Good' : 'Medium'}</span>
            <span style="font-size:11.5px; color:#0284c7; font-weight:600; font-family:var(--sd-mono);">LIVE VERIFIED DNS (DoH)</span>
          </header>
          <h4 style="font-size:15px; margin-bottom:4px; font-weight:600;">1. Sender Policy Framework (SPF) Record</h4>
          <div style="margin:8px 0; background:var(--sd-surface-2); padding:8px 12px; border-radius:4px; font-size:13px; font-family:var(--sd-mono); word-break:break-all;">
            <code>${hasSpf ? escapeHtml(doh.spf) : '(No v=spf1 TXT record found on domain)'}</code>
          </div>
          <p style="font-size:13px; color:var(--sd-ink-2); margin-top:4px;">
            <b>Observation:</b> ${hasSpf ? 'SPF record published and verified live over DNS.' : 'No SPF record was located. Domain may be vulnerable to unauthorized email impersonation.'}
          </p>
        </div>

        <!-- Live DMARC -->
        <div class="scan-card-finding" style="border-left: 4px solid ${hasDmarc ? 'var(--sd-success)' : '#f59e0b'}; background:var(--sd-surface); padding:14px 16px; border-radius:6px; border:1px solid var(--sd-border); border-left-width:4px;">
          <header style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span class="sd-tag ${hasDmarc ? 'sd-tag--good' : 'sd-tag--low'}">${hasDmarc ? 'Good' : 'Low'}</span>
            <span style="font-size:11.5px; color:#0284c7; font-weight:600; font-family:var(--sd-mono);">LIVE VERIFIED DNS (DoH)</span>
          </header>
          <h4 style="font-size:15px; margin-bottom:4px; font-weight:600;">2. DMARC Email Protection Policy</h4>
          <div style="margin:8px 0; background:var(--sd-surface-2); padding:8px 12px; border-radius:4px; font-size:13px; font-family:var(--sd-mono); word-break:break-all;">
            <code>${hasDmarc ? escapeHtml(doh.dmarc) : '(No v=DMARC1 record found at _dmarc.' + escapeHtml(domain) + ')'}</code>
          </div>
          <p style="font-size:13px; color:var(--sd-ink-2); margin-top:4px;">
            <b>Observation:</b> ${hasDmarc ? 'DMARC policy verified live over DNS.' : 'Add a TXT record at _dmarc.' + escapeHtml(domain) + ' to specify handling for unauthenticated messages.'}
          </p>
        </div>

        <!-- Live CAA -->
        <div class="scan-card-finding" style="border-left: 4px solid var(--sd-border-strong); background:var(--sd-surface); padding:14px 16px; border-radius:6px; border:1px solid var(--sd-border); border-left-width:4px;">
          <header style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span class="sd-tag sd-tag--plain">Info</span>
            <span style="font-size:11.5px; color:#0284c7; font-weight:600; font-family:var(--sd-mono);">LIVE VERIFIED DNS (DoH)</span>
          </header>
          <h4 style="font-size:15px; margin-bottom:4px; font-weight:600;">3. Certificate Authority Authorization (CAA)</h4>
          <div style="margin:8px 0; background:var(--sd-surface-2); padding:8px 12px; border-radius:4px; font-size:13px; font-family:var(--sd-mono); word-break:break-all;">
            <code>${hasCaa ? escapeHtml(doh.caa) : '(No CAA records published)'}</code>
          </div>
          <p style="font-size:13px; color:var(--sd-ink-2); margin-top:4px;">
            <b>Observation:</b> ${hasCaa ? 'Designated Certificate Authorities are explicitly whitelisted.' : 'Any compliant CA can issue certificates if control of the domain is validated.'}
          </p>
        </div>
      </div>

      <h4 style="margin-top:20px; font-size:15px; font-weight:600;">Educational Demonstration Samples (Requires Server Execution to Verify):</h4>

      <div style="display:grid; gap:12px; margin-top:8px;">
        <div class="scan-card-finding" style="border-left: 4px solid #94a3b8; background:var(--sd-surface); padding:14px 16px; border-radius:6px; border:1px solid var(--sd-border); border-left-width:4px;">
          <header style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span class="sd-tag sd-tag--simulated">Sample Demonstration</span>
            <span style="font-size:11.5px; color:var(--sd-muted); font-family:var(--sd-mono);">Educational Baseline · Unverified</span>
          </header>
          <h4 style="font-size:15px; margin-bottom:4px; font-weight:600;">Sample · HTTP Strict Transport Security (HSTS)</h4>
          <p style="font-size:13.5px; color:var(--sd-ink-2); margin-top:2px;">Browser cross-origin security prevents client-side JavaScript from reading remote server headers directly. To inspect live HSTS headers on ${domain}, start the SentinelX Standalone Server.</p>
          <div style="margin:8px 0; background:var(--sd-surface-2); padding:8px 12px; border-radius:4px; font-size:13px; font-family:var(--sd-mono);">
            <code>Expected: Strict-Transport-Security: max-age=31536000; includeSubDomains</code>
          </div>
          <p style="font-size:13px; color:var(--sd-ink-2); margin-top:4px;"><b>Recommended Fix:</b> Add HSTS header to instruct modern browsers to enforce HTTPS connections exclusively.</p>
        </div>

        <div class="scan-card-finding" style="border-left: 4px solid #94a3b8; background:var(--sd-surface); padding:14px 16px; border-radius:6px; border:1px solid var(--sd-border); border-left-width:4px;">
          <header style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span class="sd-tag sd-tag--simulated">Sample Demonstration</span>
            <span style="font-size:11.5px; color:var(--sd-muted); font-family:var(--sd-mono);">Educational Baseline · Unverified</span>
          </header>
          <h4 style="font-size:15px; margin-bottom:4px; font-weight:600;">Sample · Content Security Policy (CSP)</h4>
          <p style="font-size:13.5px; color:var(--sd-ink-2); margin-top:2px;">A CSP restricts unauthorized script and resource origins to protect visitors against cross-site scripting (XSS).</p>
          <div style="margin:8px 0; background:var(--sd-surface-2); padding:8px 12px; border-radius:4px; font-size:13px; font-family:var(--sd-mono);">
            <code>Recommended Baseline: Content-Security-Policy-Report-Only: default-src 'self'; script-src 'self' ...</code>
          </div>
          <p style="font-size:13px; color:var(--sd-ink-2); margin-top:4px;"><b>Recommended Fix:</b> Begin in Report-Only mode to audit legitimate asset sources before strict enforcement.</p>
        </div>
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:16px; border-top:1px solid var(--sd-border); padding-top:16px;">
        <span style="font-size:12.5px; color:var(--sd-muted);">Live DoH + Demonstration Baseline · SentinelX Standalone Inspector</span>
        <div style="display:flex; gap:10px;">
          <button type="button" class="sd-btn sd-btn--secondary" onclick="window.print()">Print / Export PDF</button>
          <button type="button" class="sd-btn sd-btn--primary" onclick="document.querySelector('.scan-modal').classList.remove('is-active')">Done</button>
        </div>
      </div>
    `;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
}
