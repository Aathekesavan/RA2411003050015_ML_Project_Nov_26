"""HTML View Templates for Northstar Campus Portal (SentinelX Mode 2 Isolated Replica).

Provides authentic, accessible, institutional HTML views for the fictional university portal:
- Fictional University Identity: Northstar University (fictional educational institution).
- Clean institutional design: authoritative slate-navy masthead (#0f1f38), neutral backgrounds
  (#f8fafc, #ffffff), crisp 1px borders (#e2e8f0), high-contrast accessible typography.
- Fictional student identity: Elena Vance (Undergraduate #NS-88412, Term: Fall 2026).
- Structured academic schedule, student financial accounts (OneCard), campus life, and staff gateway.
- Interactive features across all routes:
  * /replica: Campus portal overview with live announcements, quick services, and interactive balance preview.
  * /replica/portal: Full student dashboard with enrolled courses, syllabus modals, interactive OneCard deposit modal (+ $15, + $25, + $50), account statement ledger, and library booth reservations.
  * /replica/login: CAS Single Sign-On with client-side interactive login, quick-fill demo credential chips, 401 error message, and 403 block handling with live countdown timer.
  * /replica/admin: Faculty & Staff Console with student grade roster management, midterm grade saving, student search, and system operational indicators.
  * /replica/admin-decoy: Restricted Infrastructure Diagnostic Gateway (Honeypot Trap) with interactive test triggers, event challenge responses, and zero-storage privacy safeguards.
  * 403 Blocked View: Institutional security restriction screen with live countdown timer and auto-refresh when block expires.
- SVG iconography throughout; zero emojis, zero excessive gradients, zero glassmorphism.
- Zero external CDN dependencies (100% self-contained, offline-compatible).
"""

from typing import Optional, Dict, Any


def render_northstar_campus_portal(
    active_route: str = "/replica",
    client_ip: str = "127.0.0.1",
    scenario_hint: Optional[str] = None,
) -> str:
    """Generate complete, standalone, accessible HTML for Northstar Campus Portal."""
    if active_route == "/replica/login":
        return _render_sso_page(client_ip)
    elif active_route == "/replica/admin":
        return _render_admin_console_page(client_ip)
    elif active_route == "/replica/admin-decoy":
        return _render_decoy_gateway_page(client_ip, scenario_hint)
    elif active_route == "/replica/portal":
        return _render_portal_dashboard(client_ip)
    else:
        return _render_overview_page(client_ip)


def _get_common_styles() -> str:
    """Return shared institutional CSS stylesheet."""
    return """
    :root {
      --nu-navy-masthead: #0b1526;
      --nu-navy: #0f1f38;
      --nu-navy-surface: #182740;
      --nu-blue-primary: #1d4ed8;
      --nu-blue-hover: #1e40af;
      --nu-blue-subtle: #eff6ff;
      --nu-blue-border: #bfdbfe;
      --nu-bg: #f8fafc;
      --nu-surface: #ffffff;
      --nu-border: #e2e8f0;
      --nu-border-subtle: #f1f5f9;
      --nu-text-main: #0f172a;
      --nu-text-secondary: #334155;
      --nu-text-muted: #64748b;
      --nu-green: #15803d;
      --nu-green-bg: #f0fdf4;
      --nu-green-border: #bbf7d0;
      --nu-amber: #b45309;
      --nu-amber-bg: #fffbeb;
      --nu-amber-border: #fde68a;
      --nu-red: #b91c1c;
      --nu-red-bg: #fef2f2;
      --nu-red-border: #fecaca;
      --nu-font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --nu-font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: var(--nu-font);
      background-color: var(--nu-bg);
      color: var(--nu-text-main);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      -webkit-font-smoothing: antialiased;
    }

    /* Global Institutional Utility Bar */
    .nu-util-bar {
      background: var(--nu-navy-masthead);
      color: #94a3b8;
      font-size: 0.76rem;
      padding: 6px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .nu-util-bar a {
      color: #cbd5e1;
      text-decoration: none;
      transition: color 0.15s;
    }
    .nu-util-bar a:hover {
      color: #ffffff;
      text-decoration: underline;
    }
    .nu-util-links {
      display: flex;
      gap: 18px;
      align-items: center;
    }

    /* Primary Institutional Header */
    .nu-header {
      background: var(--nu-navy);
      color: #ffffff;
      padding: 14px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      border-bottom: 1px solid #1e2e4a;
    }
    .nu-brand {
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
      color: inherit;
    }
    .nu-brand:focus-visible {
      outline: 2px solid #60a5fa;
      outline-offset: 4px;
      border-radius: 4px;
    }
    .nu-brand-titles {
      display: flex;
      flex-direction: column;
    }
    .nu-brand-name {
      font-size: 0.95rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #f8fafc;
      line-height: 1.2;
    }
    .nu-portal-name {
      font-size: 0.78rem;
      color: #94a3b8;
      font-weight: 400;
    }

    /* User Monogram Profile Block */
    .nu-user-panel {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 4px 12px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 6px;
    }
    .nu-avatar {
      width: 28px;
      height: 28px;
      background: #1e3a8a;
      border: 1px solid #3b82f6;
      color: #ffffff;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.05em;
    }
    .nu-user-meta {
      font-size: 0.76rem;
      line-height: 1.25;
    }
    .nu-user-name {
      font-weight: 600;
      color: #f1f5f9;
    }
    .nu-user-id {
      color: #94a3b8;
      font-size: 0.7rem;
      font-family: var(--nu-font-mono);
    }

    /* Institutional Navigation Bar */
    .nu-nav {
      background: #ffffff;
      border-bottom: 1px solid var(--nu-border);
      padding: 0 28px;
      display: flex;
      gap: 4px;
      overflow-x: auto;
    }
    .nu-nav-link {
      padding: 10px 14px;
      font-size: 0.84rem;
      font-weight: 500;
      color: var(--nu-text-secondary);
      text-decoration: none;
      border-bottom: 2px solid transparent;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      transition: color 0.15s, border-color 0.15s;
    }
    .nu-nav-link:hover {
      color: var(--nu-blue-primary);
    }
    .nu-nav-link.active {
      color: var(--nu-blue-primary);
      font-weight: 600;
      border-bottom-color: var(--nu-blue-primary);
    }
    .nu-nav-link:focus-visible {
      outline: 2px solid var(--nu-blue-primary);
      outline-offset: -2px;
      border-radius: 2px;
    }

    /* Main Container */
    .nu-container {
      max-width: 1140px;
      width: 100%;
      margin: 20px auto;
      padding: 0 24px;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    /* Academic Standing Bar */
    .nu-profile-strip {
      background: #ffffff;
      border: 1px solid var(--nu-border);
      border-radius: 6px;
      padding: 14px 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .nu-profile-left {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .nu-profile-heading {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--nu-navy);
    }
    .nu-profile-program {
      font-size: 0.82rem;
      color: var(--nu-text-muted);
    }
    .nu-profile-stats {
      display: flex;
      gap: 16px;
      font-size: 0.8rem;
      align-items: center;
    }
    .nu-stat-item {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
    }
    .nu-stat-label {
      font-size: 0.68rem;
      color: var(--nu-text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .nu-stat-value {
      font-weight: 600;
      color: var(--nu-text-main);
      font-family: var(--nu-font-mono);
    }

    /* Official Campus Advisory Notice */
    .nu-notice {
      background: var(--nu-blue-subtle);
      border: 1px solid var(--nu-blue-border);
      border-left: 4px solid var(--nu-blue-primary);
      border-radius: 4px;
      padding: 10px 14px;
      font-size: 0.82rem;
      color: #1e3a8a;
      display: flex;
      align-items: flex-start;
      gap: 10px;
      line-height: 1.45;
    }

    /* Standard Data Tables & Content Cards */
    .nu-card {
      background: #ffffff;
      border: 1px solid var(--nu-border);
      border-radius: 6px;
      overflow: hidden;
    }
    .nu-card-header {
      padding: 12px 18px;
      border-bottom: 1px solid var(--nu-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #fafbfd;
    }
    .nu-card-title {
      font-size: 0.88rem;
      font-weight: 600;
      color: var(--nu-navy);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .nu-card-body {
      padding: 16px 18px;
    }

    /* Academic Schedule Table */
    .nu-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      text-align: left;
    }
    .nu-table th {
      background: #f8fafc;
      color: var(--nu-text-muted);
      font-weight: 600;
      padding: 8px 12px;
      border-bottom: 1px solid var(--nu-border);
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .nu-table td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--nu-border-subtle);
      color: var(--nu-text-secondary);
    }
    .nu-table tr:last-child td {
      border-bottom: none;
    }
    .nu-badge {
      display: inline-block;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.02em;
    }
    .nu-badge-success {
      background: var(--nu-green-bg);
      color: var(--nu-green);
      border: 1px solid var(--nu-green-border);
    }
    .nu-badge-neutral {
      background: #f1f5f9;
      color: #475569;
      border: 1px solid #cbd5e1;
    }
    .nu-badge-warning {
      background: var(--nu-amber-bg);
      color: var(--nu-amber);
      border: 1px solid var(--nu-amber-border);
    }
    .nu-badge-danger {
      background: var(--nu-red-bg);
      color: var(--nu-red);
      border: 1px solid var(--nu-red-border);
    }

    /* Grid Layouts */
    .nu-grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .nu-grid-3 {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 16px;
    }
    @media (max-width: 840px) {
      .nu-grid-2, .nu-grid-3 {
        grid-template-columns: 1fr;
      }
      .nu-nav {
        padding: 0 16px;
      }
      .nu-header {
        padding: 12px 16px;
      }
      .nu-util-bar {
        padding: 6px 16px;
      }
    }

    /* Key-Value Ledger List */
    .nu-ledger-list {
      display: flex;
      flex-direction: column;
    }
    .nu-ledger-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid var(--nu-border-subtle);
      font-size: 0.82rem;
    }
    .nu-ledger-item:last-child {
      border-bottom: none;
    }
    .nu-ledger-key {
      color: var(--nu-text-muted);
    }
    .nu-ledger-val {
      font-weight: 600;
      color: var(--nu-text-main);
      font-family: var(--nu-font-mono);
    }

    /* Action Buttons */
    .nu-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 7px 14px;
      font-size: 0.8rem;
      font-weight: 600;
      border-radius: 4px;
      text-decoration: none;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.15s;
    }
    .nu-btn:focus-visible {
      outline: 2px solid var(--nu-blue-primary);
      outline-offset: 2px;
    }
    .nu-btn-primary {
      background: var(--nu-blue-primary);
      color: #ffffff;
    }
    .nu-btn-primary:hover {
      background: var(--nu-blue-hover);
    }
    .nu-btn-secondary {
      background: #ffffff;
      color: var(--nu-text-secondary);
      border-color: var(--nu-border);
    }
    .nu-btn-secondary:hover {
      background: #f8fafc;
      border-color: #cbd5e1;
    }
    .nu-btn-danger {
      background: #dc2626;
      color: #ffffff;
    }
    .nu-btn-danger:hover {
      background: #b91c1c;
    }

    /* Quick Action Chips */
    .nu-chip {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      padding: 4px 10px;
      border-radius: 14px;
      font-size: 0.72rem;
      color: var(--nu-text-secondary);
      cursor: pointer;
      transition: all 0.15s;
    }
    .nu-chip:hover {
      background: #e2e8f0;
      color: var(--nu-text-main);
    }

    /* Interactive Modal */
    .nu-modal-backdrop {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(11, 18, 32, 0.75);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 16px;
    }
    .nu-modal-backdrop.open {
      display: flex;
    }
    .nu-modal-card {
      background: #ffffff;
      border: 1px solid var(--nu-border);
      border-radius: 6px;
      max-width: 480px;
      width: 100%;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      overflow: hidden;
    }
    .nu-modal-header {
      padding: 14px 18px;
      background: #fafbfd;
      border-bottom: 1px solid var(--nu-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .nu-modal-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--nu-navy);
    }
    .nu-modal-close {
      background: transparent;
      border: none;
      font-size: 1.2rem;
      color: var(--nu-text-muted);
      cursor: pointer;
      padding: 2px 6px;
      line-height: 1;
    }
    .nu-modal-close:hover {
      color: var(--nu-text-main);
    }
    .nu-modal-body {
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .nu-modal-footer {
      padding: 12px 18px;
      background: #f8fafc;
      border-top: 1px solid var(--nu-border);
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }

    /* Global Institutional Footer */
    .nu-footer {
      background: #ffffff;
      border-top: 1px solid var(--nu-border);
      padding: 16px 28px;
      font-size: 0.74rem;
      color: var(--nu-text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: auto;
    }
    .nu-footer a {
      color: var(--nu-text-secondary);
      text-decoration: none;
    }
    .nu-footer a:hover {
      text-decoration: underline;
    }
    """


def _get_common_svgs() -> Dict[str, str]:
    """Return dictionary of semantic inline SVG icons."""
    return {
        "crest": """<svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M16 2L4 7V16C4 23.5 9.1 30.5 16 32C22.9 30.5 28 23.5 28 16V7L16 2Z" fill="#1e3a8a" stroke="#3b82f6" stroke-width="1.5"/>
          <path d="M16 6L18.8 13.2L26 16L18.8 18.8L16 26L13.2 18.8L6 16L13.2 13.2L16 6Z" fill="#ffffff"/>
          <circle cx="16" cy="16" r="2.5" fill="#1e3a8a"/>
        </svg>""",
        "home": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>""",
        "book": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-0.5-5"/><path d="M6 6h10M6 10h10"/></svg>""",
        "card": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/></svg>""",
        "lock": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>""",
        "shield": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>""",
        "info": """<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="16" y2="12"/><line x1="12" x2="12.01" y1="8" y2="8"/></svg>""",
        "check": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>""",
        "user": """<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>""",
    }


def _render_layout_wrapper(
    title: str,
    active_route: str,
    client_ip: str,
    body_content: str,
    user_name: str = "Elena Vance",
    user_sub: str = "ID: NS-88412 • Fall 2026",
    avatar_text: str = "EV",
) -> str:
    """Render the standard institutional header, nav, body container, and footer."""
    svgs = _get_common_svgs()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Northstar University</title>
  <style>
    {_get_common_styles()}
  </style>
</head>
<body>

  <!-- Institutional Utility Bar -->
  <div class="nu-util-bar">
    <span>Northstar University &bull; Division of Information Technology</span>
    <div class="nu-util-links">
      <a href="/replica">Portal Home</a>
      <a href="/replica/portal">My Courses</a>
      <a href="/replica/login">Central SSO</a>
      <a href="/replica/admin">Staff Gateway</a>
      <a href="/presentation" target="_blank" style="color: #60a5fa; font-weight: 600;">SentinelX Console (Mode 2)</a>
    </div>
  </div>

  <!-- Primary Institutional Header -->
  <header class="nu-header">
    <a href="/replica" class="nu-brand" title="Northstar Campus Portal Home">
      {svgs['crest']}
      <div class="nu-brand-titles">
        <span class="nu-brand-name">Northstar University</span>
        <span class="nu-portal-name">Student Information & Campus Services Portal</span>
      </div>
    </a>
    <div class="nu-user-panel" aria-label="Authenticated Student Profile">
      <div class="nu-avatar">{avatar_text}</div>
      <div class="nu-user-meta">
        <div class="nu-user-name">{user_name}</div>
        <div class="nu-user-id">{user_sub}</div>
      </div>
    </div>
  </header>

  <!-- Institutional Navigation Bar -->
  <nav class="nu-nav" aria-label="Campus Portal Navigation">
    <a href="/replica" class="nu-nav-link {'active' if active_route == '/replica' else ''}">
      {svgs['home']} Overview
    </a>
    <a href="/replica/portal" class="nu-nav-link {'active' if active_route == '/replica/portal' else ''}">
      {svgs['book']} Course Schedule & Accounts
    </a>
    <a href="/replica/admin" class="nu-nav-link {'active' if active_route == '/replica/admin' else ''}">
      {svgs['user']} Faculty & Staff Console
    </a>
    <a href="/replica/login" class="nu-nav-link {'active' if active_route == '/replica/login' else ''}">
      {svgs['lock']} Single Sign-On
    </a>
    <a href="/replica/admin-decoy" class="nu-nav-link {'active' if active_route == '/replica/admin-decoy' else ''}" style="color: #475569;">
      {svgs['shield']} Diagnostics (Decoy)
    </a>
  </nav>

  <!-- Main Portal Content -->
  <main class="nu-container">
    {body_content}
  </main>

  <!-- Global Institutional Footer -->
  <footer class="nu-footer">
    <div>
      &copy; 2026 Northstar University &bull; Office of the Registrar &amp; Division of Information Technology &bull; All Rights Reserved.
    </div>
    <div>
      Client IP: <code style="font-family: var(--nu-font-mono);">{client_ip}</code> &bull; Mode 2 Isolated Replica Testbed
    </div>
  </footer>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# 1. OVERVIEW PAGE (/replica)
# ---------------------------------------------------------------------------

def _render_overview_page(client_ip: str) -> str:
    """Render the main campus portal overview page with working quick actions."""
    svgs = _get_common_svgs()
    content = f"""
    <!-- Academic Standing & Identification Strip -->
    <section class="nu-profile-strip" aria-label="Student Academic Profile">
      <div class="nu-profile-left">
        <h1 class="nu-profile-heading">Elena Vance</h1>
        <p class="nu-profile-program">B.S. in Computer Science &bull; Department of Electrical Engineering &amp; Computer Science</p>
      </div>
      <div class="nu-profile-stats">
        <div class="nu-stat-item">
          <span class="nu-stat-label">Academic Status</span>
          <span class="nu-badge nu-badge-success">Good Standing</span>
        </div>
        <div class="nu-stat-item">
          <span class="nu-stat-label">Cumulative GPA</span>
          <span class="nu-stat-value">3.82</span>
        </div>
        <div class="nu-stat-item">
          <span class="nu-stat-label">Enrolled Credits</span>
          <span class="nu-stat-value">12.0 Credits</span>
        </div>
        <div class="nu-stat-item">
          <span class="nu-stat-label">Term</span>
          <span class="nu-stat-value">Fall 2026</span>
        </div>
      </div>
    </section>

    <!-- Official Registrar Advisory -->
    <div class="nu-notice" role="alert" id="registrar-notice">
      {svgs['info']}
      <div style="flex: 1;">
        <strong>Registrar Enrollment Notice:</strong> The official Fall 2026 Add/Drop period concludes Friday, October 24 at 17:00 EDT. Ensure all required recitation and laboratory sections are finalized with your faculty advisor.
      </div>
      <button onclick="document.getElementById('registrar-notice').style.display='none'" style="background: none; border: none; font-size: 0.9rem; color: #1e3a8a; cursor: pointer;" title="Dismiss">&times;</button>
    </div>

    <!-- Quick Services Grid -->
    <div class="nu-grid-2">

      <!-- Course Schedule Summary -->
      <section class="nu-card">
        <div class="nu-card-header">
          <h2 class="nu-card-title">{svgs['book']} Enrolled Classes (Fall 2026)</h2>
          <a href="/replica/portal" class="nu-badge nu-badge-neutral" style="text-decoration: none;">View All (3)</a>
        </div>
        <div class="nu-card-body" style="padding: 0;">
          <table class="nu-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Title</th>
                <th>Time</th>
                <th>Room</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>CS-302</strong></td>
                <td>Distributed Systems</td>
                <td>MWF 10:00 - 11:15</td>
                <td>Turing 204</td>
              </tr>
              <tr>
                <td><strong>MATH-210</strong></td>
                <td>Linear Algebra</td>
                <td>TR 13:00 - 14:30</td>
                <td>Euler 110</td>
              </tr>
              <tr>
                <td><strong>SEC-401</strong></td>
                <td>Network Defense</td>
                <td>Fri 14:00 - 17:00</td>
                <td>Lovelace 08</td>
              </tr>
            </tbody>
          </table>
          <div style="padding: 12px 18px; border-top: 1px solid var(--nu-border); background: #fafbfd;">
            <a href="/replica/portal" class="nu-btn nu-btn-secondary" style="width: 100%;">Open Course Schedule &amp; Syllabi &rarr;</a>
          </div>
        </div>
      </section>

      <!-- Campus OneCard & Student Financials Preview -->
      <section class="nu-card">
        <div class="nu-card-header">
          <h2 class="nu-card-title">{svgs['card']} OneCard Debit &amp; Dining Balance</h2>
          <span class="nu-badge nu-badge-success">Tuition Paid</span>
        </div>
        <div class="nu-card-body">
          <div class="nu-ledger-list">
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">OneCard Debit Cash Balance</span>
              <span class="nu-ledger-val" id="ov-onecard-bal" style="color: var(--nu-green); font-size: 1.05rem;">$420.50</span>
            </div>
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Dining Dollars</span>
              <span class="nu-ledger-val">$185.00</span>
            </div>
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Student Printing Balance</span>
              <span class="nu-ledger-val">240 Pages</span>
            </div>
          </div>

          <!-- Quick deposit action -->
          <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--nu-border-subtle);">
            <div style="font-size: 0.76rem; color: var(--nu-text-muted); margin-bottom: 6px;">Quick Add Funds:</div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <button class="nu-chip" onclick="quickAddFunds(15)">+ $15.00</button>
              <button class="nu-chip" onclick="quickAddFunds(25)">+ $25.00</button>
              <button class="nu-chip" onclick="quickAddFunds(50)">+ $50.00</button>
              <a href="/replica/portal" class="nu-btn nu-btn-primary" style="margin-left: auto; padding: 4px 10px; font-size: 0.76rem;">Manage Accounts</a>
            </div>
            <div id="quick-deposit-confirm" style="display: none; margin-top: 8px; font-size: 0.74rem; color: var(--nu-green); font-weight: 600;">
              Deposit processed. Balance updated.
            </div>
          </div>
        </div>
      </section>

    </div>

    <!-- Announcements & Campus Life -->
    <div class="nu-grid-2">

      <!-- Campus Housing & Dining -->
      <section class="nu-card">
        <div class="nu-card-header">
          <h2 class="nu-card-title">Campus Housing &amp; Facility Access</h2>
          <span class="nu-badge nu-badge-neutral">North Quad</span>
        </div>
        <div class="nu-card-body">
          <div class="nu-ledger-list">
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Assigned Residence</span>
              <span class="nu-ledger-val">North Hall, Suite 4B</span>
            </div>
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Dining Plan</span>
              <span class="nu-ledger-val">Unlimited Residential Access</span>
            </div>
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Campus Parking Permit</span>
              <span class="nu-ledger-val">Zone B (#NS-2026)</span>
            </div>
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Library Study Space</span>
              <span class="nu-ledger-val" id="ov-booth-status">Booth 4 (15:00 Today)</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Campus Announcements Feed -->
      <section class="nu-card">
        <div class="nu-card-header">
          <h2 class="nu-card-title">University Announcements &amp; Events</h2>
          <span class="nu-badge nu-badge-neutral">October 2026</span>
        </div>
        <div class="nu-card-body" style="display: flex; flex-direction: column; gap: 10px; font-size: 0.8rem;">
          <div style="border-bottom: 1px solid var(--nu-border-subtle); padding-bottom: 8px;">
            <strong style="color: var(--nu-navy);">Fall 2026 Engineering Career Fair</strong>
            <p style="color: var(--nu-text-muted); font-size: 0.74rem;">Thursday, Oct 29 &bull; 10:00 - 16:00 EDT &bull; Campus Student Center Hall A</p>
          </div>
          <div style="border-bottom: 1px solid var(--nu-border-subtle); padding-bottom: 8px;">
            <strong style="color: var(--nu-navy);">Division of IT Maintenance Window</strong>
            <p style="color: var(--nu-text-muted); font-size: 0.74rem;">Sunday, 02:00 - 04:00 EDT: Routine core network switch firmware update.</p>
          </div>
          <div>
            <strong style="color: var(--nu-navy);">Lovelace Science Library 24/7 Hours</strong>
            <p style="color: var(--nu-text-muted); font-size: 0.74rem;">Beginning next Monday, Lovelace Library will operate 24 hours daily for midterms.</p>
          </div>
        </div>
      </section>

    </div>

    <!-- Faculty & Administrative Gateway (Institutional Notice) -->
    <section class="nu-profile-strip" style="border-left: 4px solid #475569;" aria-label="Staff Administrative Gateway">
      <div>
        <h3 style="font-size: 0.92rem; font-weight: 700; color: var(--nu-navy);">Faculty &amp; Staff Administrative Services</h3>
        <p style="font-size: 0.78rem; color: var(--nu-text-muted);">Access faculty grade submission, course roster management, and infrastructure diagnostic tools.</p>
      </div>
      <div style="display: flex; gap: 8px; flex-wrap: wrap;">
        <a href="/replica/admin" class="nu-btn nu-btn-secondary">Faculty Console</a>
        <a href="/replica/login" class="nu-btn nu-btn-secondary">Staff SSO Sign-In</a>
        <a href="/replica/admin-decoy" class="nu-btn nu-btn-secondary" style="color: #64748b;">Systems Diagnostics (Decoy)</a>
      </div>
    </section>

    <script>
      function getStoredBalance() {{
        const b = localStorage.getItem('nu_onecard_bal');
        return b ? parseFloat(b) : 420.50;
      }}
      function setStoredBalance(val) {{
        localStorage.setItem('nu_onecard_bal', val.toFixed(2));
        const el = document.getElementById('ov-onecard-bal');
        if (el) el.textContent = '$' + val.toFixed(2);
      }}
      function quickAddFunds(amount) {{
        const cur = getStoredBalance();
        const next = cur + amount;
        setStoredBalance(next);
        const confirmEl = document.getElementById('quick-deposit-confirm');
        if (confirmEl) {{
          confirmEl.style.display = 'block';
          confirmEl.textContent = 'Deposited $' + amount.toFixed(2) + '. New Balance: $' + next.toFixed(2);
          setTimeout(() => {{ confirmEl.style.display = 'none'; }}, 3000);
        }}
      }}
      document.addEventListener('DOMContentLoaded', () => {{
        const el = document.getElementById('ov-onecard-bal');
        if (el) el.textContent = '$' + getStoredBalance().toFixed(2);
      }});
    </script>
    """
    return _render_layout_wrapper(
        title="Campus Portal Overview",
        active_route="/replica",
        client_ip=client_ip,
        body_content=content,
    )


# ---------------------------------------------------------------------------
# 2. STUDENT PORTAL DASHBOARD (/replica/portal)
# ---------------------------------------------------------------------------

def _render_portal_dashboard(client_ip: str) -> str:
    """Render the full student portal with course syllabus modals, interactive OneCard deposits, and transaction ledger."""
    svgs = _get_common_svgs()
    content = f"""
    <!-- Student Header Strip -->
    <section class="nu-profile-strip" aria-label="Student Academic Profile">
      <div class="nu-profile-left">
        <h1 class="nu-profile-heading">Elena Vance</h1>
        <p class="nu-profile-program">B.S. in Computer Science &bull; Department of Electrical Engineering &amp; Computer Science</p>
      </div>
      <div class="nu-profile-stats">
        <div class="nu-stat-item">
          <span class="nu-stat-label">Academic Standing</span>
          <span class="nu-badge nu-badge-success">Good Standing</span>
        </div>
        <div class="nu-stat-item">
          <span class="nu-stat-label">Class Year</span>
          <span class="nu-stat-value">Junior (Year 3)</span>
        </div>
        <div class="nu-stat-item">
          <span class="nu-stat-label">Term Credits</span>
          <span class="nu-stat-value">12.0 Enrolled</span>
        </div>
      </div>
    </section>

    <!-- Primary Schedule Table -->
    <section class="nu-card" aria-label="Enrolled Courses">
      <div class="nu-card-header">
        <h2 class="nu-card-title">{svgs['book']} Enrolled Course Schedule &mdash; Fall 2026</h2>
        <span class="nu-badge nu-badge-neutral">3 Registered Classes</span>
      </div>
      <table class="nu-table">
        <thead>
          <tr>
            <th scope="col">Course Code</th>
            <th scope="col">Course Title</th>
            <th scope="col">Instructor</th>
            <th scope="col">Class Meeting Time</th>
            <th scope="col">Classroom</th>
            <th scope="col">Status</th>
            <th scope="col">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>CS-302</strong></td>
            <td>Distributed Systems &amp; Concurrency</td>
            <td>Prof. M. Thorne</td>
            <td>Mon, Wed, Fri 10:00 - 11:15</td>
            <td>Turing Hall 204</td>
            <td><span class="nu-badge nu-badge-success">Enrolled</span></td>
            <td>
              <button class="nu-btn nu-btn-secondary" style="padding: 3px 8px; font-size: 0.72rem;" onclick="openSyllabusModal('CS-302', 'Distributed Systems & Concurrency', 'Prof. M. Thorne', 'Turing Hall 204', 'Consensus protocols, Raft, Paxos, distributed transactions, vector clocks, and RPC architectures.')">View Syllabus</button>
            </td>
          </tr>
          <tr>
            <td><strong>MATH-210</strong></td>
            <td>Linear Algebra &amp; Applications</td>
            <td>Dr. S. Chen</td>
            <td>Tue, Thu 13:00 - 14:30</td>
            <td>Euler Hall 110</td>
            <td><span class="nu-badge nu-badge-success">Enrolled</span></td>
            <td>
              <button class="nu-btn nu-btn-secondary" style="padding: 3px 8px; font-size: 0.72rem;" onclick="openSyllabusModal('MATH-210', 'Linear Algebra & Applications', 'Dr. S. Chen', 'Euler Hall 110', 'Vector spaces, linear transformations, matrices, determinants, eigenvalues, eigenvectors, and singular value decomposition.')">View Syllabus</button>
            </td>
          </tr>
          <tr>
            <td><strong>SEC-401</strong></td>
            <td>Network Defense &amp; System Auditing</td>
            <td>Staff Faculty</td>
            <td>Friday 14:00 - 17:00</td>
            <td>Lovelace Lab 08</td>
            <td><span class="nu-badge nu-badge-success">Enrolled</span></td>
            <td>
              <button class="nu-btn nu-btn-secondary" style="padding: 3px 8px; font-size: 0.72rem;" onclick="openSyllabusModal('SEC-401', 'Network Defense & System Auditing', 'Staff Faculty', 'Lovelace Lab 08', 'Intrusion detection, packet inspection, network flow analysis, access control lists, firewalls, and decoy defensive architectures.')">View Syllabus</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Two-Column Financial & Residential Ledger -->
    <section class="nu-grid-2" id="onecard">
      
      <!-- Student Accounts & OneCard -->
      <article class="nu-card" aria-label="Student Accounts">
        <div class="nu-card-header">
          <h2 class="nu-card-title">{svgs['card']} Campus OneCard &amp; Student Financials</h2>
          <span class="nu-badge nu-badge-success">Tuition Paid</span>
        </div>
        <div class="nu-card-body">
          <div class="nu-ledger-list">
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Term Tuition &amp; Mandatory Fees</span>
              <span class="nu-ledger-val">$15,420.50</span>
            </div>
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">OneCard Debit Cash Balance</span>
              <span class="nu-ledger-val" id="portal-onecard-bal" style="color: var(--nu-green); font-size: 1.1rem;">$420.50</span>
            </div>
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Campus Dining Dollars</span>
              <span class="nu-ledger-val">$185.00</span>
            </div>
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Student Printing Allocation</span>
              <span class="nu-ledger-val">240 Pages Left</span>
            </div>
          </div>
          <div style="margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap;">
            <button class="nu-btn nu-btn-primary" onclick="openDepositModal()">+ Add OneCard Funds</button>
            <button class="nu-btn nu-btn-secondary" onclick="toggleStatementLedger()">Account Statement &darr;</button>
          </div>
        </div>
      </article>

      <!-- Campus Housing & Facility Access -->
      <article class="nu-card" aria-label="Campus Housing">
        <div class="nu-card-header">
          <h2 class="nu-card-title">Campus Housing &amp; Residential Life</h2>
          <span class="nu-badge nu-badge-neutral">North Quad</span>
        </div>
        <div class="nu-card-body">
          <div class="nu-ledger-list">
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Residential Assignment</span>
              <span class="nu-ledger-val">North Hall, Suite 4B</span>
            </div>
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Residential Dining Plan</span>
              <span class="nu-ledger-val">Unlimited Residential Access</span>
            </div>
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Campus Parking Permit</span>
              <span class="nu-ledger-val">Zone B (Permit #NS-2026)</span>
            </div>
            <div class="nu-ledger-item">
              <span class="nu-ledger-key">Library Study Space Reservation</span>
              <span class="nu-ledger-val" id="booth-reservation-status">Booth 4 (15:00 Today)</span>
            </div>
          </div>
          <div style="margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap;">
            <button class="nu-btn nu-btn-secondary" onclick="reserveStudySpace()">Reserve Library Booth</button>
            <button class="nu-btn nu-btn-secondary" onclick="alert('Housing Agreement: Active for 2026-2027 Academic Year. North Hall Suite 4B.')">Housing Agreement</button>
          </div>
        </div>
      </article>

    </section>

    <!-- Expandable Account Statement Ledger -->
    <section class="nu-card" id="account-statement-section" style="display: none;">
      <div class="nu-card-header">
        <h2 class="nu-card-title">{svgs['card']} OneCard Transaction Statement Ledger</h2>
        <span class="nu-badge nu-badge-neutral">Fall 2026 Activity</span>
      </div>
      <div class="nu-card-body" style="padding: 0;">
        <table class="nu-table" id="transaction-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Reference ID</th>
              <th>Description</th>
              <th>Category</th>
              <th style="text-align: right;">Amount</th>
              <th style="text-align: right;">Running Balance</th>
            </tr>
          </thead>
          <tbody id="transaction-tbody">
            <tr>
              <td>2026-10-20 14:15</td>
              <td><code>TX-99014</code></td>
              <td>Northstar Bookstore (Course Pack CS-302)</td>
              <td><span class="nu-badge nu-badge-neutral">Bookstore</span></td>
              <td style="text-align: right; color: var(--nu-red);">- $42.50</td>
              <td style="text-align: right; font-family: var(--nu-font-mono);">$420.50</td>
            </tr>
            <tr>
              <td>2026-10-18 12:30</td>
              <td><code>TX-98921</code></td>
              <td>Student Union Dining Center</td>
              <td><span class="nu-badge nu-badge-neutral">Dining</span></td>
              <td style="text-align: right; color: var(--nu-red);">- $14.20</td>
              <td style="text-align: right; font-family: var(--nu-font-mono);">$463.00</td>
            </tr>
            <tr>
              <td>2026-10-15 09:00</td>
              <td><code>TX-98502</code></td>
              <td>Parent Deposit (Mastercard &bull;&bull;&bull;&bull; 4812)</td>
              <td><span class="nu-badge nu-badge-success">Deposit</span></td>
              <td style="text-align: right; color: var(--nu-green);">+ $150.00</td>
              <td style="text-align: right; font-family: var(--nu-font-mono);">$477.20</td>
            </tr>
            <tr>
              <td>2026-10-01 10:00</td>
              <td><code>TX-97810</code></td>
              <td>Fall Term Initial Account Allocation</td>
              <td><span class="nu-badge nu-badge-success">Deposit</span></td>
              <td style="text-align: right; color: var(--nu-green);">+ $350.00</td>
              <td style="text-align: right; font-family: var(--nu-font-mono);">$327.20</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Modal: Add OneCard Funds -->
    <div class="nu-modal-backdrop" id="deposit-modal">
      <div class="nu-modal-card">
        <div class="nu-modal-header">
          <div class="nu-modal-title">{svgs['card']} Add Campus OneCard Funds</div>
          <button class="nu-modal-close" onclick="closeDepositModal()">&times;</button>
        </div>
        <div class="nu-modal-body">
          <p style="font-size: 0.8rem; color: var(--nu-text-muted);">
            Funds added are available immediately across all campus dining halls, bookstore, student print stations, and vending terminals.
          </p>
          <div>
            <label style="display: block; font-size: 0.76rem; font-weight: 600; color: var(--nu-text-secondary); margin-bottom: 6px;">Select Amount:</label>
            <div style="display: flex; gap: 8px;">
              <button type="button" class="nu-btn nu-btn-secondary" onclick="selectDepositAmount(15)">$15.00</button>
              <button type="button" class="nu-btn nu-btn-secondary" onclick="selectDepositAmount(25)">$25.00</button>
              <button type="button" class="nu-btn nu-btn-secondary" onclick="selectDepositAmount(50)">$50.00</button>
              <button type="button" class="nu-btn nu-btn-secondary" onclick="selectDepositAmount(100)">$100.00</button>
            </div>
          </div>
          <div>
            <label for="deposit-custom-input" style="display: block; font-size: 0.76rem; font-weight: 600; color: var(--nu-text-secondary); margin-bottom: 4px;">Custom Amount ($):</label>
            <input type="number" id="deposit-custom-input" min="5" max="500" step="5" value="25.00" style="width: 100%; padding: 8px 10px; border: 1px solid var(--nu-border); border-radius: 4px; font-size: 0.85rem; font-family: var(--nu-font-mono);">
          </div>
          <div>
            <label for="deposit-method" style="display: block; font-size: 0.76rem; font-weight: 600; color: var(--nu-text-secondary); margin-bottom: 4px;">Payment Method:</label>
            <select id="deposit-method" style="width: 100%; padding: 8px 10px; border: 1px solid var(--nu-border); border-radius: 4px; font-size: 0.82rem; background: #ffffff;">
              <option value="bank">Northstar Credit Union &bull;&bull;&bull;&bull; 4812 (Checking)</option>
              <option value="card">Mastercard &bull;&bull;&bull;&bull; 9012 (Saved)</option>
            </select>
          </div>
          <div id="modal-deposit-status" style="display: none; padding: 8px 12px; border-radius: 4px; font-size: 0.76rem;"></div>
        </div>
        <div class="nu-modal-footer">
          <button class="nu-btn nu-btn-secondary" onclick="closeDepositModal()">Cancel</button>
          <button class="nu-btn nu-btn-primary" onclick="submitDepositFunds()">Confirm &amp; Deposit Funds</button>
        </div>
      </div>
    </div>

    <!-- Modal: Course Syllabus -->
    <div class="nu-modal-backdrop" id="syllabus-modal">
      <div class="nu-modal-card">
        <div class="nu-modal-header">
          <div class="nu-modal-title" id="syl-modal-title">Course Syllabus</div>
          <button class="nu-modal-close" onclick="closeSyllabusModal()">&times;</button>
        </div>
        <div class="nu-modal-body">
          <div style="font-size: 0.8rem; display: flex; flex-direction: column; gap: 8px;">
            <div><strong>Instructor:</strong> <span id="syl-modal-inst"></span></div>
            <div><strong>Location:</strong> <span id="syl-modal-loc"></span></div>
            <div><strong>Description:</strong> <p id="syl-modal-desc" style="color: var(--nu-text-muted); margin-top: 4px; line-height: 1.4;"></p></div>
            <div style="background: #f8fafc; border: 1px solid var(--nu-border); border-radius: 4px; padding: 10px; margin-top: 6px;">
              <strong>Grading Scheme:</strong>
              <ul style="margin-left: 20px; margin-top: 4px; color: var(--nu-text-secondary); font-size: 0.76rem;">
                <li>Lab Assignments &amp; Projects: 40%</li>
                <li>Midterm Examination: 25%</li>
                <li>Final Capstone: 30%</li>
                <li>Class Participation: 5%</li>
              </ul>
            </div>
          </div>
        </div>
        <div class="nu-modal-footer">
          <button class="nu-btn nu-btn-primary" onclick="closeSyllabusModal()">Close</button>
        </div>
      </div>
    </div>

    <script>
      function getStoredBalance() {{
        const b = localStorage.getItem('nu_onecard_bal');
        return b ? parseFloat(b) : 420.50;
      }}
      function updateBalanceDisplay() {{
        const b = getStoredBalance();
        const el = document.getElementById('portal-onecard-bal');
        if (el) el.textContent = '$' + b.toFixed(2);
      }}
      function openDepositModal() {{
        document.getElementById('deposit-modal').classList.add('open');
      }}
      function closeDepositModal() {{
        document.getElementById('deposit-modal').classList.remove('open');
      }}
      function selectDepositAmount(amt) {{
        document.getElementById('deposit-custom-input').value = amt.toFixed(2);
      }}
      function submitDepositFunds() {{
        const input = document.getElementById('deposit-custom-input');
        const amt = parseFloat(input.value);
        if (isNaN(amt) || amt <= 0) {{
          alert('Please enter a valid deposit amount.');
          return;
        }}
        const cur = getStoredBalance();
        const next = cur + amt;
        localStorage.setItem('nu_onecard_bal', next.toFixed(2));
        updateBalanceDisplay();

        // Add to statement table
        const tbody = document.getElementById('transaction-tbody');
        if (tbody) {{
          const nowStr = new Date().toISOString().slice(0, 16).replace('T', ' ');
          const txId = 'TX-' + Math.floor(10000 + Math.random() * 90000);
          const tr = document.createElement('tr');
          tr.style.backgroundColor = '#f0fdf4';
          tr.innerHTML = `
            <td>${{nowStr}}</td>
            <td><code>${{txId}}</code></td>
            <td>Online Deposit (Card &bull;&bull;&bull;&bull; 9012)</td>
            <td><span class="nu-badge nu-badge-success">Deposit</span></td>
            <td style="text-align: right; color: var(--nu-green);">+ $${{amt.toFixed(2)}}</td>
            <td style="text-align: right; font-family: var(--nu-font-mono);">$${{next.toFixed(2)}}</td>
          `;
          tbody.insertBefore(tr, tbody.firstChild);
        }}

        const statusEl = document.getElementById('modal-deposit-status');
        statusEl.style.display = 'block';
        statusEl.style.background = '#dcfce7';
        statusEl.style.color = '#15803d';
        statusEl.style.border = '1px solid #bbf7d0';
        statusEl.textContent = 'Deposit confirmed: $' + amt.toFixed(2) + '. New balance: $' + next.toFixed(2);

        setTimeout(() => {{
          statusEl.style.display = 'none';
          closeDepositModal();
        }}, 1400);
      }}

      function toggleStatementLedger() {{
        const sec = document.getElementById('account-statement-section');
        if (sec.style.display === 'none') {{
          sec.style.display = 'block';
          sec.scrollIntoView({{ behavior: 'smooth' }});
        }} else {{
          sec.style.display = 'none';
        }}
      }}

      function openSyllabusModal(code, title, inst, loc, desc) {{
        document.getElementById('syl-modal-title').textContent = code + ': ' + title;
        document.getElementById('syl-modal-inst').textContent = inst;
        document.getElementById('syl-modal-loc').textContent = loc;
        document.getElementById('syl-modal-desc').textContent = desc;
        document.getElementById('syllabus-modal').classList.add('open');
      }}
      function closeSyllabusModal() {{
        document.getElementById('syllabus-modal').classList.remove('open');
      }}

      function reserveStudySpace() {{
        const el = document.getElementById('booth-reservation-status');
        const nextTime = 'Booth 4 (Confirmed ' + new Date().toLocaleTimeString([], {{hour: '2-digit', minute:'2-digit'}}) + ')';
        el.textContent = nextTime;
        alert('Study space reserved! Reservation confirmed for Lovelace Library Study Booth 4.');
      }}

      document.addEventListener('DOMContentLoaded', () => {{
        updateBalanceDisplay();
      }});
    </script>
    """
    return _render_layout_wrapper(
        title="Student Dashboard & Accounts",
        active_route="/replica/portal",
        client_ip=client_ip,
        body_content=content,
    )


# ---------------------------------------------------------------------------
# 3. SINGLE SIGN-ON CAS PAGE (/replica/login)
# ---------------------------------------------------------------------------

def _render_sso_page(client_ip: str) -> str:
    """Render the official Northstar University Central Authentication Service (CAS / SSO)."""
    svgs = _get_common_svgs()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Central Authentication Service | Northstar University</title>
  <style>
    {_get_common_styles()}
    body {{
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .sso-card {{
      background: #ffffff;
      border: 1px solid var(--nu-border);
      border-radius: 8px;
      max-width: 440px;
      width: 100%;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      overflow: hidden;
    }}
    .sso-header {{
      background: var(--nu-navy);
      color: #ffffff;
      padding: 22px 24px;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
    }}
    .sso-title {{
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .sso-subtitle {{
      font-size: 0.78rem;
      color: #94a3b8;
    }}
    .sso-body {{
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .sso-field {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .sso-label {{
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--nu-text-secondary);
    }}
    .sso-input {{
      padding: 8px 10px;
      border: 1px solid var(--nu-border);
      border-radius: 4px;
      font-size: 0.85rem;
      color: var(--nu-text-main);
      background: #fcfdfe;
      transition: border-color 0.15s;
    }}
    .sso-input:focus {{
      outline: none;
      border-color: var(--nu-blue-primary);
      box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.12);
    }}
    .sso-demo-chips {{
      display: flex;
      gap: 6px;
      margin-top: 4px;
      flex-wrap: wrap;
    }}
    .sso-chip-btn {{
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.68rem;
      color: #475569;
      cursor: pointer;
      font-weight: 600;
    }}
    .sso-chip-btn:hover {{
      background: #e2e8f0;
      color: #0f172a;
    }}
    .sso-btn {{
      background: var(--nu-blue-primary);
      color: #ffffff;
      border: none;
      padding: 10px 14px;
      border-radius: 4px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: background 0.15s;
    }}
    .sso-btn:hover {{
      background: var(--nu-blue-hover);
    }}
    .sso-alert-box {{
      display: none;
      padding: 10px 14px;
      border-radius: 4px;
      font-size: 0.78rem;
      line-height: 1.4;
    }}
    .sso-footer {{
      background: #f8fafc;
      border-top: 1px solid var(--nu-border);
      padding: 12px 24px;
      font-size: 0.72rem;
      color: var(--nu-text-muted);
      text-align: center;
    }}
  </style>
</head>
<body>

  <main class="sso-card">
    <div class="sso-header">
      {svgs['crest']}
      <div>
        <h1 class="sso-title">Northstar University</h1>
        <p class="sso-subtitle">Central Authentication Service (CAS / Shibboleth SSO)</p>
      </div>
    </div>

    <!-- Live Status / Error Banner -->
    <div id="sso-alert" class="sso-alert-box" style="margin: 16px 24px 0 24px;"></div>

    <form class="sso-body" id="sso-form" onsubmit="handleSsoSubmit(event)">
      <div class="sso-field">
        <label class="sso-label" for="username">Northstar NetID or University Email</label>
        <input class="sso-input" type="text" id="username" name="username" value="admin" required autocomplete="username">
      </div>

      <div class="sso-field">
        <label class="sso-label" for="password">Password</label>
        <input class="sso-input" type="password" id="password" name="password" value="ReplicaLab2026!" required autocomplete="current-password">
      </div>

      <!-- Demo Credentials Quick Selector -->
      <div>
        <span style="font-size: 0.68rem; color: var(--nu-text-muted);">Demo Credential Shortcuts:</span>
        <div class="sso-demo-chips">
          <button type="button" class="sso-chip-btn" onclick="fillCreds('admin', 'ReplicaLab2026!')">Valid NetID (admin)</button>
          <button type="button" class="sso-chip-btn" onclick="fillCreds('admin', 'AttackerSprayFail999!')">Invalid Password (401)</button>
        </div>
      </div>

      <button type="submit" class="sso-btn" id="sso-submit-btn">
        {svgs['lock']} Sign In to Campus Services
      </button>

      <p style="font-size: 0.72rem; color: var(--nu-text-muted); line-height: 1.4; text-align: center; margin-top: 4px;">
        Restricted institutional access. Login telemetry is audited by the SentinelX Mode 2 Replica Guard.
      </p>
    </form>

    <div class="sso-footer">
      Connected Source Address: <code style="font-family: var(--nu-font-mono);">{client_ip}</code> &bull; Isolated Replica
    </div>
  </main>

  <div style="margin-top: 16px; display: flex; gap: 14px; font-size: 0.78rem;">
    <a href="/replica" style="color: var(--nu-blue-primary); text-decoration: none;">&larr; Campus Portal Overview</a>
    <span style="color: var(--nu-border);">&bull;</span>
    <a href="/replica/admin" style="color: var(--nu-text-secondary); text-decoration: none;">Staff Administrative Console</a>
  </div>

  <script>
    function fillCreds(u, p) {{
      document.getElementById('username').value = u;
      document.getElementById('password').value = p;
    }}

    async function handleSsoSubmit(e) {{
      e.preventDefault();
      const u = document.getElementById('username').value;
      const p = document.getElementById('password').value;
      const alertBox = document.getElementById('sso-alert');
      const submitBtn = document.getElementById('sso-submit-btn');

      submitBtn.disabled = true;
      submitBtn.textContent = 'Verifying Credentials...';

      try {{
        const resp = await fetch('/replica/login', {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }},
          body: JSON.stringify({{ username: u, password: p }})
        }});

        const data = await resp.json();

        if (resp.status === 200) {{
          alertBox.style.display = 'block';
          alertBox.style.background = '#f0fdf4';
          alertBox.style.color = '#15803d';
          alertBox.style.border = '1px solid #bbf7d0';
          alertBox.innerHTML = '<strong>Authentication Successful:</strong> Redirecting to student dashboard...';
          setTimeout(() => {{
            window.location.href = '/replica/portal';
          }}, 900);
        }} else if (resp.status === 403) {{
          const detail = data.detail || {{}};
          alertBox.style.display = 'block';
          alertBox.style.background = '#fef2f2';
          alertBox.style.color = '#991b1b';
          alertBox.style.border = '1px solid #fecaca';
          alertBox.innerHTML = '<strong>Access Denied &mdash; HTTP 403:</strong> ' + (detail.message || 'Access blocked by SentinelX Mode 2 Replica Defense.') + '<br><small>Block active. Expires in: ' + (detail.ttl_remaining_seconds || 15) + 's</small>';
          submitBtn.disabled = false;
          submitBtn.innerHTML = '{svgs['lock']} Sign In to Campus Services';
        }} else {{
          // 401 Unauthorized
          const msg = data.detail ? data.detail.message : 'Invalid NetID or password.';
          alertBox.style.display = 'block';
          alertBox.style.background = '#fffbeb';
          alertBox.style.color = '#b45309';
          alertBox.style.border = '1px solid #fde68a';
          alertBox.innerHTML = '<strong>Authentication Failed:</strong> ' + msg + '<br><small>Security Notice: Repeated failed logins will trigger an automated network block.</small>';
          submitBtn.disabled = false;
          submitBtn.innerHTML = '{svgs['lock']} Sign In to Campus Services';
        }}
      }} catch (err) {{
        alertBox.style.display = 'block';
        alertBox.style.background = '#fef2f2';
        alertBox.style.color = '#991b1b';
        alertBox.style.border = '1px solid #fecaca';
        alertBox.textContent = 'Network communication error: ' + err.message;
        submitBtn.disabled = false;
        submitBtn.innerHTML = '{svgs['lock']} Sign In to Campus Services';
      }}
    }}
  </script>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# 4. FACULTY & STAFF ADMIN CONSOLE (/replica/admin)
# ---------------------------------------------------------------------------

def _render_admin_console_page(client_ip: str) -> str:
    """Render the official Faculty & Staff Administrative Management Console."""
    svgs = _get_common_svgs()
    content = f"""
    <!-- Faculty Profile Header Strip -->
    <section class="nu-profile-strip" style="border-left: 4px solid #1e3a8a;">
      <div class="nu-profile-left">
        <h1 class="nu-profile-heading">Prof. Marcus Thorne, Ph.D.</h1>
        <p class="nu-profile-program">Department of Electrical Engineering &amp; Computer Science &bull; Faculty ID: #FAC-0149</p>
      </div>
      <div class="nu-profile-stats">
        <div class="nu-stat-item">
          <span class="nu-stat-label">System Role</span>
          <span class="nu-badge nu-badge-neutral">Tenured Faculty / Course Head</span>
        </div>
        <div class="nu-stat-item">
          <span class="nu-stat-label">Assigned Sections</span>
          <span class="nu-stat-value">CS-302 (Section 01)</span>
        </div>
        <div class="nu-stat-item">
          <span class="nu-stat-label">Term Status</span>
          <span class="nu-badge nu-badge-success">Roster Finalized</span>
        </div>
      </div>
    </section>

    <!-- Operational System Status -->
    <div class="nu-grid-3">
      <div class="nu-card" style="padding: 12px 16px;">
        <span style="font-size: 0.68rem; color: var(--nu-text-muted); text-transform: uppercase; font-weight: 700;">Registrar DB Pool</span>
        <div style="font-size: 0.95rem; font-weight: 700; color: var(--nu-green); margin-top: 2px;">ONLINE (12ms)</div>
        <span style="font-size: 0.7rem; color: var(--nu-text-muted);">Active connections: 8 / 20</span>
      </div>
      <div class="nu-card" style="padding: 12px 16px;">
        <span style="font-size: 0.68rem; color: var(--nu-text-muted); text-transform: uppercase; font-weight: 700;">SSO Directory Sync</span>
        <div style="font-size: 0.95rem; font-weight: 700; color: var(--nu-green); margin-top: 2px;">SYNCHRONIZED</div>
        <span style="font-size: 0.7rem; color: var(--nu-text-muted);">Last sync: 4 minutes ago</span>
      </div>
      <div class="nu-card" style="padding: 12px 16px;">
        <span style="font-size: 0.68rem; color: var(--nu-text-muted); text-transform: uppercase; font-weight: 700;">SentinelX Threat Guard</span>
        <div style="font-size: 0.95rem; font-weight: 700; color: #0284c7; margin-top: 2px;">ACTIVE (Mode 2)</div>
        <span style="font-size: 0.7rem; color: var(--nu-text-muted);">Isolated local replica testbed</span>
      </div>
    </div>

    <!-- Course Roster & Grade Submission -->
    <section class="nu-card">
      <div class="nu-card-header">
        <h2 class="nu-card-title">{svgs['book']} CS-302: Distributed Systems &mdash; Student Roster &amp; Grades</h2>
        <div style="display: flex; gap: 8px; align-items: center;">
          <input type="text" id="roster-search" placeholder="Search student name or NetID..." onkeyup="filterRoster()" style="padding: 4px 8px; font-size: 0.75rem; border: 1px solid var(--nu-border); border-radius: 4px;">
          <span class="nu-badge nu-badge-neutral">4 Students Registered</span>
        </div>
      </div>
      <div class="nu-card-body" style="padding: 0;">
        <table class="nu-table" id="roster-table">
          <thead>
            <tr>
              <th>Student Name</th>
              <th>NetID</th>
              <th>Program</th>
              <th>Attendance</th>
              <th>Midterm Grade</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Elena Vance</strong></td>
              <td><code>evance88</code></td>
              <td>B.S. Computer Science</td>
              <td>98% (14 / 14 lectures)</td>
              <td>
                <select style="padding: 2px 6px; font-size: 0.76rem; border-radius: 3px; border: 1px solid var(--nu-border);">
                  <option selected>A- (92%)</option>
                  <option>A (95%)</option>
                  <option>B+ (88%)</option>
                </select>
              </td>
              <td><span class="nu-badge nu-badge-success">Good Standing</span></td>
            </tr>
            <tr>
              <td><strong>Marcus Brody</strong></td>
              <td><code>mbrody12</code></td>
              <td>B.S. Software Engineering</td>
              <td>92% (13 / 14 lectures)</td>
              <td>
                <select style="padding: 2px 6px; font-size: 0.76rem; border-radius: 3px; border: 1px solid var(--nu-border);">
                  <option>A- (92%)</option>
                  <option selected>B+ (88%)</option>
                  <option>B (84%)</option>
                </select>
              </td>
              <td><span class="nu-badge nu-badge-success">Good Standing</span></td>
            </tr>
            <tr>
              <td><strong>Priya Patel</strong></td>
              <td><code>ppatel44</code></td>
              <td>B.S. Computer Engineering</td>
              <td>100% (14 / 14 lectures)</td>
              <td>
                <select style="padding: 2px 6px; font-size: 0.76rem; border-radius: 3px; border: 1px solid var(--nu-border);">
                  <option selected>A (96%)</option>
                  <option>A- (92%)</option>
                </select>
              </td>
              <td><span class="nu-badge nu-badge-success">Dean's List</span></td>
            </tr>
            <tr>
              <td><strong>Sarah Connor</strong></td>
              <td><code>sconnor01</code></td>
              <td>B.S. Information Systems</td>
              <td>85% (12 / 14 lectures)</td>
              <td>
                <select style="padding: 2px 6px; font-size: 0.76rem; border-radius: 3px; border: 1px solid var(--nu-border);">
                  <option>B+ (88%)</option>
                  <option selected>B (83%)</option>
                  <option>C+ (78%)</option>
                </select>
              </td>
              <td><span class="nu-badge nu-badge-neutral">Regular</span></td>
            </tr>
          </tbody>
        </table>
        <div style="padding: 12px 18px; border-top: 1px solid var(--nu-border); background: #fafbfd; display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.75rem; color: var(--nu-text-muted);">Midterm grade changes are logged with audit timestamps.</span>
          <button class="nu-btn nu-btn-primary" onclick="saveRosterGrades()">Save Midterm Roster Grades</button>
        </div>
      </div>
    </section>

    <div id="save-toast" style="display: none; padding: 10px 16px; background: #dcfce7; border: 1px solid #bbf7d0; color: #15803d; border-radius: 4px; font-size: 0.8rem; font-weight: 600;">
      Grades successfully recorded to Northstar Registrar Database.
    </div>

    <script>
      function filterRoster() {{
        const q = document.getElementById('roster-search').value.toLowerCase();
        const rows = document.querySelectorAll('#roster-table tbody tr');
        rows.forEach(r => {{
          r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
        }});
      }}
      function saveRosterGrades() {{
        const toast = document.getElementById('save-toast');
        toast.style.display = 'block';
        setTimeout(() => {{ toast.style.display = 'none'; }}, 3000);
      }}
    </script>
    """
    return _render_layout_wrapper(
        title="Faculty & Staff Administrative Console",
        active_route="/replica/admin",
        client_ip=client_ip,
        body_content=content,
        user_name="Prof. Marcus Thorne",
        user_sub="Faculty #FAC-0149 • EECS Dept",
        avatar_text="MT",
    )


# ---------------------------------------------------------------------------
# 5. HONEYPOT DECOY GATEWAY (/replica/admin-decoy)
# ---------------------------------------------------------------------------

def _render_decoy_gateway_page(client_ip: str, scenario_hint: Optional[str] = None) -> str:
    """Render the restricted Systems Diagnostics Gateway (SentinelX Mode 2 Honeypot Trap)."""
    svgs = _get_common_svgs()
    content = f"""
    <!-- Decoy Security Banner -->
    <div class="nu-card" style="border-left: 4px solid #b91c1c;">
      <div class="nu-card-body" style="display: flex; align-items: flex-start; gap: 14px;">
        <div style="width: 38px; height: 38px; border-radius: 6px; background: #fee2e2; display: flex; align-items: center; justify-content: center; color: #b91c1c; flex-shrink: 0;">
          {svgs['shield']}
        </div>
        <div style="flex: 1;">
          <h1 style="font-size: 1.05rem; font-weight: 700; color: #991b1b; margin-bottom: 2px;">
            Institutional Infrastructure Diagnostics Gateway &mdash; Monitored Security Decoy
          </h1>
          <p style="font-size: 0.8rem; color: #7f1d1d; line-height: 1.45;">
            <strong>RESTRICTED ACCESS WARNING:</strong> This administrative diagnostics route is a defensive decoy trap monitored by SentinelX Mode 2. All probe interactions, scanning signatures, and unauthorized requests are logged as high-confidence honeypot signals for automated temporary source blocking.
          </p>
          <div style="margin-top: 8px; font-size: 0.74rem; color: #475569; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px 10px;">
            <strong>Strict Privacy Safeguard:</strong> The decoy records security event metadata only (source IP, timestamp, HTTP method, route). It does <em>not</em> store submitted passphrases, credentials, or request bodies.
          </div>
        </div>
      </div>
    </div>

    <!-- Interactive Diagnostics Diagnostic Form -->
    <div style="max-width: 540px; margin: 0 auto; width: 100%;">
      <section class="nu-card">
        <div class="nu-card-header">
          <h2 class="nu-card-title">{svgs['lock']} Core Infrastructure Diagnostics Trigger</h2>
          <span class="nu-badge nu-badge-danger">Decoy Honeypot Trap</span>
        </div>
        <form class="nu-card-body" id="decoy-form" onsubmit="handleDecoySubmit(event)">
          <div style="display: flex; flex-direction: column; gap: 12px;">
            <div>
              <label for="subsystem" style="display: block; font-size: 0.78rem; font-weight: 600; color: var(--nu-text-secondary); margin-bottom: 4px;">Target Subsystem:</label>
              <select id="subsystem" style="width: 100%; padding: 8px 10px; border: 1px solid var(--nu-border); border-radius: 4px; font-size: 0.82rem; background: #ffffff;">
                <option value="pg_pool">PostgreSQL Campus Database Pool (port 5432)</option>
                <option value="radius_aaa">RADIUS AAA Authentication Gateway</option>
                <option value="core_bgp">Campus Core BGP Routing Table</option>
                <option value="ldap_dir">Active Directory / LDAP User Store</option>
              </select>
            </div>
            <div>
              <label for="decoy-passphrase" style="display: block; font-size: 0.78rem; font-weight: 600; color: var(--nu-text-secondary); margin-bottom: 4px;">Internal Maintenance Passphrase:</label>
              <input type="password" id="decoy-passphrase" placeholder="Enter administrative diagnostic token..." value="DecoyProbeAttempt2026!" style="width: 100%; padding: 8px 10px; border: 1px solid var(--nu-border); border-radius: 4px; font-size: 0.82rem; font-family: var(--nu-font-mono);">
            </div>
            <button type="submit" id="decoy-submit-btn" class="nu-btn nu-btn-danger" style="margin-top: 6px;">
              Initiate Core Diagnostic Dump &rarr;
            </button>
          </div>
        </form>
        <div id="decoy-result" style="display: none; padding: 14px 18px; border-top: 1px solid var(--nu-border); background: #fef2f2; font-size: 0.78rem;"></div>
      </section>
    </div>

    <script>
      async function handleDecoySubmit(e) {{
        e.preventDefault();
        const btn = document.getElementById('decoy-submit-btn');
        const resBox = document.getElementById('decoy-result');
        btn.disabled = true;
        btn.textContent = 'Submitting Diagnostic Request...';

        try {{
          const resp = await fetch('/replica/admin-decoy', {{
            method: 'POST',
            headers: {{
              'Accept': 'application/json',
              'Content-Type': 'application/json'
            }},
            body: JSON.stringify({{ target: document.getElementById('subsystem').value }})
          }});

          const data = await resp.json();

          if (resp.status === 403) {{
            const detail = data.detail || {{}};
            resBox.style.display = 'block';
            resBox.style.background = '#fef2f2';
            resBox.style.color = '#991b1b';
            resBox.innerHTML = '<strong>ACCESS BLOCKED &mdash; HTTP 403:</strong> ' + (detail.message || 'Access blocked by SentinelX Mode 2 Replica Defense.') + '<br><small>Block active for source IP. TTL Remaining: ' + (detail.ttl_remaining_seconds || 15) + 's</small>';
          }} else {{
            resBox.style.display = 'block';
            resBox.style.background = '#fef2f2';
            resBox.style.color = '#991b1b';
            resBox.innerHTML = '<strong>CHALLENGE REQUIRED (Honeypot Triggered):</strong><br>' +
              '&bull; Status: ' + data.status + '<br>' +
              '&bull; Security Event ID: <code>' + data.event_id + '</code><br>' +
              '&bull; Captured at: ' + data.timestamp + '<br>' +
              '<small style="display:block; margin-top: 6px; color: #7f1d1d;">Incident telemetry has been correlated to SentinelX Guard queue.</small>';
          }}
        }} catch (err) {{
          resBox.style.display = 'block';
          resBox.textContent = 'Communication error: ' + err.message;
        }} finally {{
          btn.disabled = false;
          btn.textContent = 'Initiate Core Diagnostic Dump \u2192';
        }}
      }}
    </script>
    """
    return _render_layout_wrapper(
        title="Infrastructure Diagnostics (Decoy)",
        active_route="/replica/admin-decoy",
        client_ip=client_ip,
        body_content=content,
        user_name="Decoy Gateway",
        user_sub="Route: /replica/admin-decoy",
        avatar_text="DG",
    )


# ---------------------------------------------------------------------------
# 6. AUTHENTIC 403 BLOCKED PAGE
# ---------------------------------------------------------------------------

def render_replica_blocked_page(detail: Dict[str, Any]) -> str:
    """Render an authentic university institutional HTTP 403 Access Denied block page."""
    svgs = _get_common_svgs()
    target_ip = detail.get("target_ip", "127.0.0.1")
    route = detail.get("route", "/replica")
    reason = detail.get("reason", "Automated threat defense policy violation.")
    ttl_rem = detail.get("ttl_remaining_seconds", 15)
    exp = detail.get("expires_at", "soon")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>403 Access Restricted | Northstar Information Security</title>
  <style>
    {_get_common_styles()}
    body {{
      align-items: center;
      justify-content: center;
      padding: 24px;
      background-color: #0f172a;
      color: #f8fafc;
    }}
    .block-card {{
      background: #1e293b;
      border: 2px solid #dc2626;
      border-radius: 6px;
      max-width: 520px;
      width: 100%;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
      overflow: hidden;
    }}
    .block-header {{
      background: #7f1d1d;
      color: #ffffff;
      padding: 18px 24px;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .block-title {{
      font-size: 1.05rem;
      font-weight: 700;
    }}
    .block-body {{
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .block-detail-box {{
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 12px 14px;
      font-size: 0.8rem;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .block-timer-box {{
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 14px 16px;
      text-align: center;
    }}
    .block-countdown {{
      font-family: var(--nu-font-mono);
      font-size: 1.6rem;
      font-weight: 700;
      color: #fbbf24;
      margin: 4px 0;
    }}
    .block-progress-track {{
      background: #334155;
      height: 6px;
      border-radius: 3px;
      overflow: hidden;
      margin-top: 8px;
    }}
    .block-progress-fill {{
      background: #ef4444;
      height: 100%;
      transition: width 1s linear;
    }}
  </style>
</head>
<body>

  <main class="block-card">
    <div class="block-header">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fca5a5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
      <div>
        <h1 class="block-title">Access Restricted &mdash; HTTP 403</h1>
        <div style="font-size: 0.74rem; color: #fecaca;">Northstar Information Security Office &bull; Gateway Defense</div>
      </div>
    </div>

    <div class="block-body">
      <p style="font-size: 0.84rem; color: #cbd5e1; line-height: 1.45;">
        Connection from client IP <code style="color: #fca5a5; font-family: var(--nu-font-mono);">{target_ip}</code> to target route <code style="color: #93c5fd; font-family: var(--nu-font-mono);">{route}</code> has been temporarily restricted by the SentinelX Mode 2 Replica Defense system.
      </p>

      <div class="block-detail-box">
        <div><strong style="color: #94a3b8;">Enforcement Reason:</strong> <span style="color: #f1f5f9;">{reason}</span></div>
        <div><strong style="color: #94a3b8;">Source Host:</strong> <code style="color: #f8fafc; font-family: var(--nu-font-mono);">{target_ip}</code></div>
        <div><strong style="color: #94a3b8;">Enforcing Adapter:</strong> <span style="color: #cbd5e1;">LocalReplicaAdapter (In-Process)</span></div>
        <div><strong style="color: #94a3b8;">Scheduled Expiry:</strong> <span style="color: #cbd5e1; font-family: var(--nu-font-mono);">{exp}</span></div>
      </div>

      <div class="block-timer-box">
        <div style="font-size: 0.74rem; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.04em;">Temporary Block Active</div>
        <div class="block-countdown" id="live-ttl">{ttl_rem}s</div>
        <div class="block-progress-track">
          <div class="block-progress-fill" id="ttl-bar" style="width: 100%;"></div>
        </div>
        <p style="font-size: 0.72rem; color: #94a3b8; margin-top: 8px;">
          Access returns automatically when this timer ends, or immediately if reset from the SentinelX presentation console.
        </p>
      </div>

      <div style="display: flex; gap: 10px; justify-content: space-between; margin-top: 4px;">
        <a href="/presentation" style="padding: 8px 14px; background: #3b82f6; color: #ffffff; text-decoration: none; border-radius: 4px; font-size: 0.78rem; font-weight: 600;">
          Open SentinelX Presentation Console &rarr;
        </a>
        <a href="/replica" style="padding: 8px 14px; background: #334155; color: #f8fafc; text-decoration: none; border-radius: 4px; font-size: 0.78rem;">
          Retry Connection
        </a>
      </div>
    </div>
  </main>

  <script>
    let rem = {ttl_rem};
    const total = Math.max(1, rem);
    const ttlEl = document.getElementById('live-ttl');
    const barEl = document.getElementById('ttl-bar');

    const timer = setInterval(() => {{
      rem--;
      if (rem <= 0) {{
        clearInterval(timer);
        if (ttlEl) ttlEl.textContent = '0s';
        if (barEl) barEl.style.width = '0%';
        setTimeout(() => {{
          window.location.reload();
        }}, 800);
      }} else {{
        if (ttlEl) ttlEl.textContent = rem + 's';
        if (barEl) barEl.style.width = Math.max(0, (rem / total) * 100) + '%';
      }}
    }}, 1000);
  </script>

</body>
</html>
"""
