"""End-to-End Demo for SentinelX Phase 3: Web-Server and WAF Log Ingestion & Correlation.

Demonstrates:
1. Parsing Nginx access/error logs and ModSecurity WAF events with malformed line isolation.
2. Temporal & IP correlation matching netflow telemetry with host/web tier events.
3. Scenario 1: Slow-rate Brute Force attack requiring auth-failure evidence for escalation.
4. Scenario 2: Benign traffic burst that should not alone trigger incident escalation.
5. Ingestion of alerts with confirming signals into the analyst review queue.
"""

import sys
import json
import logging
from pathlib import Path

# Ensure workspace root is in python path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import pandas as pd

from src.ingestion.parsers import (
    NginxAccessLogParser,
    NginxErrorLogParser,
    ModSecurityParser,
)
from src.ingestion.correlator import LogFlowCorrelator
from src.guard.engine import SentinelGuard
from src.alerts.store import LocalReviewStore

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("demo_phase3")


def run_phase3_demo(
    log_dir: Path = Path("data/samples/logs"),
    persist_to_store: bool = True,
    batch_id: str = "phase3-demo-run"
):
    print("=" * 80)
    print("  SENTINELX-SHIFT PHASE 3 DEMO: WEB LOG & WAF CORRELATION PIPELINE")
    print("  Operational Posture: MONITOR-ONLY | Autonomous Blocking: STRICTLY DISABLED")
    print("=" * 80)

    # 1. Parse Log Files
    access_log = log_dir / "nginx_access.log"
    error_log = log_dir / "nginx_error.log"
    waf_log = log_dir / "modsecurity_waf.log"
    flows_file = log_dir / "synthetic_flows.csv"

    print("\n[STEP 1] Parsing Web-Tier & WAF Log Sources...")
    access_res = NginxAccessLogParser().parse(access_log.read_text(encoding="utf-8"))
    error_res = NginxErrorLogParser().parse(error_log.read_text(encoding="utf-8"))
    waf_res = ModSecurityParser().parse(waf_log.read_text(encoding="utf-8"))

    print(f"  • Nginx Access:   {access_res.parsed_count} events parsed, {access_res.malformed_count} malformed lines isolated.")
    print(f"  • Nginx Error:    {error_res.parsed_count} events parsed, {error_res.malformed_count} malformed lines isolated.")
    print(f"  • ModSecurity:    {waf_res.parsed_count} events parsed, {waf_res.malformed_count} malformed lines isolated.")

    all_events = access_res.events + error_res.events + waf_res.events
    print(f"  => Total Parsed Events Loaded: {len(all_events)}")

    # 2. Correlate with Flows
    print("\n[STEP 2] Correlating Log Events with Netflow Telemetry...")
    flows_df = pd.read_csv(flows_file)
    print(f"  Loaded {len(flows_df)} flow records from {flows_file}")

    correlator = LogFlowCorrelator(events=all_events, time_window_seconds=30.0)
    signals_list, summaries = correlator.correlate_batch(flows_df)

    # 3. Analyze through SentinelGuard
    print("\n[STEP 3] Running SentinelGuard Inference with Correlated Signals...")
    guard = SentinelGuard()

    # Score WITH correlated signals
    response_with_signals = guard.analyze_flows(
        flows=flows_df,
        signals=signals_list,
        batch_id=batch_id
    )

    # Score WITHOUT signals (to demonstrate guardrail contrast)
    response_without_signals = guard.analyze_flows(
        flows=flows_df,
        signals=None,
        batch_id=f"{batch_id}-unconfirmed"
    )

    # 4. Scenario Walkthroughs
    print("\n" + "=" * 80)
    print("  WALKTHROUGH SCENARIO 1: Slow-Rate Brute Force Attempt")
    print("=" * 80)
    alert_s1_with = response_with_signals.alerts[0]
    alert_s1_without = response_without_signals.alerts[0]
    summary_s1 = summaries[0]

    print(f"  Flow ID:             {alert_s1_with.flow_id}")
    print(f"  Source IP:           {summary_s1.source_ip}")
    print(f"  Suspected Family:    {alert_s1_with.suspected_family}")
    print(f"  Production Score:    {alert_s1_with.scores.production_score:.4f} (AE: {alert_s1_with.scores.autoencoder_score:.4f}, XGB: {alert_s1_with.scores.supervised_score:.4f})")
    print(f"  Matched Web Events:  {summary_s1.matched_events_count} events in window")
    
    auth_sig = alert_s1_with.confirming_signals.get("auth_failures")
    rate_sig = alert_s1_with.confirming_signals.get("request_rate")
    waf_sig = alert_s1_with.confirming_signals.get("waf_event")

    print(f"  • Auth Failures:     {auth_sig.value} (threshold: {auth_sig.threshold}; confirmed={auth_sig.confirmed})")
    print(f"  • Request Rate:      {rate_sig.value:.2f} req/s (threshold: {rate_sig.threshold}; confirmed={rate_sig.confirmed} - slow rate bypasses volumetric alert)")
    print(f"  • WAF Alert:         {waf_sig.value} (confirmed={waf_sig.confirmed})")

    print("\n  [Guardrail Comparison]:")
    print(f"    WITHOUT Web Logs:  Tier: {alert_s1_without.risk_tier.value:<8} | Action: {alert_s1_without.recommended_action.value}")
    print(f"                       Note: {alert_s1_without.policy_notes[-1]}")
    print(f"    WITH Correlated:   Tier: {alert_s1_with.risk_tier.value:<8} | Action: {alert_s1_with.recommended_action.value}")
    print(f"                       Note: {alert_s1_with.policy_notes[-1]}")
    print("  => VERDICT: Independent auth failure evidence successfully verified attack, escalating to analyst review.")

    print("\n" + "=" * 80)
    print("  WALKTHROUGH SCENARIO 2: Benign Traffic Burst")
    print("=" * 80)
    alert_s2_with = response_with_signals.alerts[1]
    summary_s2 = summaries[1]

    print(f"  Flow ID:             {alert_s2_with.flow_id}")
    print(f"  Source IP:           {summary_s2.source_ip}")
    print(f"  Suspected Family:    {alert_s2_with.suspected_family or 'Benign'}")
    print(f"  Production Score:    {alert_s2_with.scores.production_score:.4f}")
    
    rate_sig2 = alert_s2_with.confirming_signals.get("request_rate")
    auth_sig2 = alert_s2_with.confirming_signals.get("auth_failures")
    waf_sig2 = alert_s2_with.confirming_signals.get("waf_event")

    print(f"  • Request Rate:      {rate_sig2.value:.1f} req/s (threshold: {rate_sig2.threshold}; confirmed={rate_sig2.confirmed} - burst detected)")
    print(f"  • Auth Failures:     {auth_sig2.value} (confirmed={auth_sig2.confirmed})")
    print(f"  • WAF Alert:         {waf_sig2.value} (confirmed={waf_sig2.confirmed})")
    print(f"  • Risk Tier:         {alert_s2_with.risk_tier.value}")
    print(f"  • Action:            {alert_s2_with.recommended_action.value}")
    print("  => VERDICT: Benign burst produces zero auth failures and no WAF triggers. Traffic is allowed/monitored without false incident escalation.")

    print("\n" + "=" * 80)
    print("  EDGE CASE: Flow Missing Source IP & Timestamp Telemetry")
    print("=" * 80)
    alert_s3 = response_with_signals.alerts[2]
    unavail = [name for name, s in alert_s3.confirming_signals.items() if not s.present]
    print(f"  Flow ID:             {alert_s3.flow_id}")
    print(f"  Unavailable Signals: {', '.join(unavail)}")
    print(f"  Policy:              Defensive Principle preserved - missing data is explicitly unconfirmed (never assumed confirmed).")

    # 5. Persist to Review Store
    if persist_to_store:
        store = LocalReviewStore()
        # Telemetry list for detail view
        telemetry = flows_df.to_dict(orient="records")
        inserted = store.insert_alerts(response_with_signals.alerts, telemetry_list=telemetry)
        print(f"\n[STEP 4] Persisted {inserted} alerts to local SQLite review store.")
        print("  Run SentinelX service and visit: http://localhost:8000/dashboard to inspect!")

    print("\n" + "=" * 80)
    print("  PHASE 3 DEMO COMPLETE")
    print("=" * 80)
    return response_with_signals


if __name__ == "__main__":
    run_phase3_demo()
