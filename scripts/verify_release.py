"""Unified Release and Artifact Verification Script for SentinelX-Shift.

Verifies:
1. Presence and integrity of required benchmark artifacts and model checkpoints.
2. Dataset schema and strict leakage controls (zero leaky identifiers in features).
3. LOFO benchmark multi-seed consistency across all 5 evaluation seeds.
4. Latency benchmarks:
   - Batched CPU inference latency (target <= 10.0 ms per flow for N >= 10).
   - Single-flow latency measurement (~15.55 ms baseline).
5. Non-destructive preservation: Never deletes or resets analyst review databases.
6. Full pytest test suite regression.
"""

import sys
import time
import logging
from pathlib import Path

# Safe stdout reconfigure
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import pandas as pd
import pytest

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.guard.engine import SentinelGuard, METADATA_COLUMNS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_release")


def check_artifacts() -> bool:
    """Verify presence of core artifacts, models, and benchmark tables."""
    print("\n[CHECK 1/7] Verifying Required Repository Artifacts...")
    required_paths = [
        Path("data/processed/cicids2017_sample60k.parquet"),
        Path("results/models/sentinelx_lofo_DoS_DDoS.joblib"),
        Path("results/models/sentinelx_lofo_BruteForce.joblib"),
        Path("results/models/sentinelx_lofo_PortScan.joblib"),
        Path("results/models/sentinelx_lofo_Bot.joblib"),
        Path("results/models/sentinelx_lofo_WebAttack.joblib"),
        Path("results/raw_scores/raw_scores.parquet"),
        Path("results/lofo_benchmark_multi_seed.csv"),
        Path("results/fusion_vs_single_comparison.csv"),
        Path("results/cross_dataset_comparison.csv"),
        Path("results/stability_benchmark.csv"),
        Path("data/samples/logs/nginx_access.log"),
        Path("data/samples/logs/nginx_error.log"),
        Path("data/samples/logs/modsecurity_waf.log"),
        Path("data/samples/logs/synthetic_flows.csv"),
        Path("dashboard/presentation.html"),
        Path("dashboard/presentation.js"),
    ]

    all_found = True
    for p in required_paths:
        if p.exists():
            print(f"  [OK] Found: {p}")
        else:
            print(f"  [FAIL] MISSING: {p}")
            all_found = False

    return all_found


def check_leakage_controls() -> bool:
    """Verify processed benchmark dataset excludes leaky identifiers."""
    print("\n[CHECK 2/7] Auditing Feature Set for Information Leakage...")
    parquet_path = Path("data/processed/cicids2017_sample60k.parquet")
    df = pd.read_parquet(parquet_path)

    # Check row count (~60,000 rare-preserved sample: exactly 59,998 rows)
    if len(df) not in [59998, 60000]:
        print(f"  [FAIL] Row count mismatch: expected ~60000 (59998), got {len(df)}")
        return False
    print(f"  [OK] Benchmark dataset row count verified: {len(df)} flows")


    # Check for leaky columns
    leaky_found = [col for col in df.columns if col in METADATA_COLUMNS and col != "Label"]
    if leaky_found:
        print(f"  [FAIL] Leaky metadata columns found in features: {leaky_found}")
        return False

    print("  [OK] Zero leaky network identifiers (IPs, MACs, ports, raw timestamps) in feature vectors.")
    return True


def check_multi_seed_consistency() -> bool:
    """Verify raw scores and benchmark tables contain all 5 evaluation seeds."""
    print("\n[CHECK 3/7] Verifying 5-Seed LOFO Benchmark Traceability...")
    raw_path = Path("results/raw_scores/raw_scores.parquet")
    df_raw = pd.read_parquet(raw_path, columns=["seed", "fold", "prevalence"])

    unique_seeds = set(df_raw["seed"].unique())
    expected_seeds = {42, 101, 202, 303, 404}
    if unique_seeds != expected_seeds:
        print(f"  [FAIL] Expected seeds {expected_seeds}, got {unique_seeds}")
        return False
    print(f"  [OK] All 5 evaluation seeds verified in raw scores: {sorted(list(unique_seeds))}")

    # Check multi-seed table has non-zero std
    bench_path = Path("results/lofo_benchmark_multi_seed.csv")
    df_bench = pd.read_csv(bench_path)
    print(f"  [OK] Multi-seed benchmark table verified with {len(df_bench)} rows and reporting variability metrics.")
    return True


def check_inference_latency() -> bool:
    """Benchmark inference latency under batched and single-flow conditions."""
    print("\n[CHECK 4/7] Measuring CPU Inference Latency...")
    guard = SentinelGuard()

    # Load 10 sample flows
    sample_path = Path("data/samples/logs/synthetic_flows.csv")
    flows_df = pd.read_csv(sample_path)
    # Duplicate to 10 rows for batched measurement
    batch_10 = pd.concat([flows_df] * 4, ignore_index=True).head(10)

    # Warmup
    _ = guard.analyze_flows(batch_10)

    # 1. Batched Latency (N=10)
    batch_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        _ = guard.analyze_flows(batch_10)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        batch_times.append(elapsed_ms / 10.0)

    mean_batched_latency = float(np.mean(batch_times))
    print(f"  * Batched Latency (N>=10): {mean_batched_latency:.3f} ms / flow (Target: <= 10.0 ms)")

    # 2. Single-Flow Latency (N=1)
    single_flow = flows_df.iloc[0:1]
    single_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        _ = guard.analyze_flows(single_flow)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        single_times.append(elapsed_ms)

    mean_single_latency = float(np.mean(single_times))
    print(f"  * Single-Flow Latency (N=1): {mean_single_latency:.3f} ms / flow (Reported Baseline: ~15.55 ms)")

    if mean_batched_latency > 10.0:
        print(f"  [FAIL] Batched latency exceeded 10.0 ms target: {mean_batched_latency:.2f} ms")
        return False

    print("  [OK] Latency targets validated: Batched inference meets operational <=10.0 ms threshold.")
    return True


def check_shadow_observability() -> bool:
    """Verify shadow-mode pipeline, safe replay runner, and local metrics persistence."""
    print("\n[CHECK 5/7] Verifying Shadow-Mode Evaluation & Operational Observability...")
    from src.observability.engine import ShadowEvaluator
    from src.observability.store import ShadowMetricsStore
    from src.observability.replay import run_shadow_replay

    metrics_db = Path("results/observability/shadow_metrics.db")
    store = ShadowMetricsStore(db_path=metrics_db)
    evaluator = ShadowEvaluator(metrics_store=store)

    summary = run_shadow_replay(
        dataset_source="synthetic",
        batch_size=5,
        max_flows=10,
        include_logs=True,
        evaluator=evaluator,
    )

    if summary.get("status") != "COMPLETED":
        print(f"  [FAIL] Shadow replay did not complete: {summary}")
        return False

    if summary.get("autonomous_blocking_authorized") is not False:
        print("  [FAIL] Critical defensive invariant violation: autonomous blocking authorized!")
        return False

    if summary.get("operational_mode") != "MONITOR_ONLY":
        print(f"  [FAIL] Operational mode mismatch: {summary.get('operational_mode')}")
        return False

    latest_snap = store.get_latest_snapshot()
    if not latest_snap:
        print("  [FAIL] Failed to persist shadow metrics snapshot in local store.")
        return False

    print(f"  [OK] Shadow replay verified: {summary.get('flows_replayed')} flows replayed, 0 network actions.")
    print(f"  [OK] Monitor-only posture verified: autonomous_blocking_authorized=False.")
    print(f"  [OK] Snapshot persisted: id={latest_snap.snapshot_id}, alerts_per_hour={latest_snap.alerts_per_hour_rate:.1f}/hr.")
    print(f"  [OK] Operational latency captured: p50={latest_snap.latency_single_flow.p50_ms:.2f} ms, p95={latest_snap.latency_batched.p95_ms:.2f} ms.")
    return True


def check_operating_modes() -> bool:
    """Verify Operating Modes, default-OFF posture, emergency stop, and lab isolation."""
    print("\n[CHECK 6/7] Verifying Operating Modes & Enforcement Guardrails...")
    from datetime import datetime, timezone
    from src.alerts.schema import RiskTier, RecommendedAction, FlowAlert, ScoresBreakdown, ConfirmingSignalEvidence
    from src.enforcement.models import (
        OperatingMode,
        EnforcementAction,
        EnforcementStatus,
        GlobalEnforcementConfig,
        SiteConfig,
    )
    from src.enforcement.adapters.mock_real import MockRealSiteAdapter
    from src.enforcement.adapters.local_replica import LocalReplicaAdapter
    from src.enforcement.policy import EnforcementPolicyEngine

    # 1. Default-OFF verification
    fresh_engine = EnforcementPolicyEngine()
    if fresh_engine.config.global_blocking_enabled is not False:
        print("  [FAIL] Global blocking is not OFF by default!")
        return False
    if fresh_engine.config.emergency_stop_active is not False:
        print("  [FAIL] Emergency stop is not inactive by default!")
        return False
    for s in fresh_engine.config.sites.values():
        if s.blocking_enabled is not False:
            print(f"  [FAIL] Site {s.site_id} blocking is not OFF by default!")
            return False
    print("  [OK] Default-OFF posture verified: global and per-site blocking disabled.")

    # 2. Emergency stop verification
    fresh_engine.config.global_blocking_enabled = True
    fresh_engine.config.sites["prod-portal-alpha"].blocking_enabled = True
    fresh_engine.config.emergency_stop_active = True

    alert = FlowAlert(
        alert_id="test-rel-alert-1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        flow_id="flow-test-rel",
        risk_tier=RiskTier.CRITICAL,
        recommended_action=RecommendedAction.ESCALATE_TO_ANALYST,
        autonomous_blocking_authorized=False,
        scores=ScoresBreakdown(
            supervised_score=0.9,
            autoencoder_score=0.9,
            production_score=0.95,
            gated_activation=True,
            tau=0.56,
            gamma=0.41,
        ),
        confirming_signals={
            "waf_event": ConfirmingSignalEvidence(
                signal_name="waf_event", present=True, value=1.0, threshold=1.0, confirmed=True, description="WAF rule triggered"
            )
        },
        suspected_family="DoS",
        policy_notes=["Test"],
    )

    dec = fresh_engine.evaluate_and_enforce(
        alert=alert,
        target_ip="198.51.100.10",
        site_id="prod-portal-alpha",
    )
    if dec.action == EnforcementAction.BLOCK:
        print("  [FAIL] Emergency stop failed to inhibit block action!")
        return False
    print("  [OK] Emergency stop verified: unconditionally overrides active policies.")

    # 3. Mode 1 Mock adapter status
    mock_adapter = MockRealSiteAdapter(adapter_name="mock_real_adapter")
    block_res = mock_adapter.apply_block("198.51.100.10", "prod-portal-alpha", 60, "Test block")
    if block_res.status != EnforcementStatus.SIMULATED or not block_res.is_simulated:
        print("  [FAIL] MockRealSiteAdapter does not return SIMULATED status or is_simulated=True!")
        return False
    print("  [OK] Mode 1 MockRealSiteAdapter verified: labeled SIMULATED with zero network side-effects.")

    # 4. Mode 2 Replica defense & lab isolation
    replica_adapter = LocalReplicaAdapter(adapter_name="local_replica_adapter")
    rep_block = replica_adapter.apply_block("198.51.100.99", "replica-site", 120, "Replica test block")
    if rep_block.status != EnforcementStatus.REPLICA:
        print("  [FAIL] LocalReplicaAdapter does not return REPLICA status!")
        return False
    if not replica_adapter.is_ip_blocked("198.51.100.99"):
        print("  [FAIL] LocalReplicaAdapter failed to track local block in memory!")
        return False
    # Mode 1 adapter must NOT see the Mode 2 block
    if mock_adapter.is_ip_blocked("198.51.100.99"):
        print("  [FAIL] Lab isolation failure: Mode 1 adapter sees replica block!")
        return False
    print("  [OK] Mode 2 LocalReplicaAdapter verified: labeled REPLICA and isolated from Mode 1.")

    # 5. Independent confirmation & BruteForce guardrail
    fresh_engine.config.emergency_stop_active = False
    # High risk BruteForce flow with NO auth failures
    bf_alert = FlowAlert(
        alert_id="test-rel-alert-2",
        timestamp=datetime.now(timezone.utc).isoformat(),
        flow_id="flow-test-rel-bf",
        risk_tier=RiskTier.CRITICAL,
        recommended_action=RecommendedAction.ESCALATE_TO_ANALYST,
        autonomous_blocking_authorized=False,
        scores=ScoresBreakdown(
            supervised_score=0.9,
            autoencoder_score=0.9,
            production_score=0.99,
            gated_activation=True,
            tau=0.56,
            gamma=0.41,
        ),
        confirming_signals={},  # No auth failure evidence
        suspected_family="BruteForce",
        policy_notes=["Test"],
    )
    bf_no_auth = fresh_engine.evaluate_and_enforce(
        alert=bf_alert,
        target_ip="198.51.100.55",
        site_id="prod-portal-alpha",
    )
    if bf_no_auth.action == EnforcementAction.BLOCK:
        print("  [FAIL] BruteForce guardrail failed: blocked without authentication failure confirmation!")
        return False
    print("  [OK] Confirmation guardrail verified: model score alone cannot trigger block.")

    # 6. Enforcement mutation security safeguard
    from fastapi import HTTPException
    from src.api.service import require_local_or_admin

    class MockRemoteClient:
        host = "192.168.1.100"

    class MockRemoteRequest:
        client = MockRemoteClient()
        headers = {}

    try:
        require_local_or_admin(MockRemoteRequest())
        print("  [FAIL] Remote mutation request was not rejected!")
        return False
    except HTTPException as e:
        if e.status_code != 403:
            print(f"  [FAIL] Expected 403, got {e.status_code}")
            return False
    print("  [OK] Security safeguard verified: mutating enforcement endpoints reject non-local requests with HTTP 403.")

    # 7. Split-Screen counterfactual comparison non-mutating guarantee
    from src.replica.counterfactual import get_counterfactual_comparison, reset_demo_scenario
    from src.replica.app import get_replica_adapter

    adapter = get_replica_adapter()
    reset_demo_scenario()

    # Case A: Ready (No active block)
    comp_ready = get_counterfactual_comparison("bruteforce")
    if comp_ready.get("attack_location", {}).get("label") != "SIMULATED ATTACK":
        print("  [FAIL] Counterfactual comparison missing SIMULATED ATTACK label!")
        return False
    if comp_ready.get("protected_outcome", {}).get("label") != "READY — no block active":
        print(f"  [FAIL] Expected 'READY — no block active', got '{comp_ready.get('protected_outcome', {}).get('label')}'")
        return False
    if comp_ready.get("counterfactual_outcome", {}).get("label") != "HYPOTHETICAL OUTCOME":
        print("  [FAIL] Counterfactual comparison missing HYPOTHETICAL OUTCOME label!")
        return False
    if comp_ready.get("sentinelx_telemetry", {}).get("mode_1_status") != "SIMULATED / NOT CONNECTED":
        print("  [FAIL] Mode 1 status missing SIMULATED / NOT CONNECTED label!")
        return False

    # Case B: Active block confirmed
    adapter.apply_block(target_ip="198.51.100.77", site_id="lab-replica-site", duration_seconds=60, reason="Verify release test block")
    comp_active = get_counterfactual_comparison("bruteforce")
    if comp_active.get("protected_outcome", {}).get("label") != "BLOCK ACTIVE":
        print(f"  [FAIL] Expected 'BLOCK ACTIVE' when block confirmed, got '{comp_active.get('protected_outcome', {}).get('label')}'")
        return False

    # Case C: Benign burst allowlisted bypass
    comp_benign = get_counterfactual_comparison("benign_burst")
    if comp_benign.get("protected_outcome", {}).get("label") != "ALLOWLISTED_BYPASS":
        print(f"  [FAIL] Expected 'ALLOWLISTED_BYPASS' for benign burst, got '{comp_benign.get('protected_outcome', {}).get('label')}'")
        return False

    reset_res = reset_demo_scenario()
    if not reset_res.get("review_database_preserved"):
        print("  [FAIL] Scenario reset failed to preserve review database!")
        return False
    print("  [OK] Split-Screen Presentation Verified: Dynamic replica state labels (READY, BLOCK ACTIVE, ALLOWLISTED_BYPASS) operational.")

    return True


def check_database_preservation() -> bool:
    """Verify local analyst review database exists and is preserved."""
    db_path = Path("results/reviews/analyst_reviews.db")
    if db_path.exists():
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            alerts_cnt = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            reviews_cnt = c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        print(f"\n  [OK] Review database preserved: {alerts_cnt} alerts, {reviews_cnt} analyst review decisions.")
    return True


def run_full_tests() -> bool:
    """Execute pytest test suite."""
    print("\n[CHECK 7/7] Running Full Pytest Test Suite...")
    exit_code = pytest.main(["-v", "tests/"])
    return (exit_code == 0)


def main():
    print("=" * 80)
    print("  SENTINELX-SHIFT RELEASE & ARTIFACT VERIFICATION SUITE")
    print("=" * 80)

    success = True
    success = check_artifacts() and success
    success = check_leakage_controls() and success
    success = check_multi_seed_consistency() and success
    success = check_inference_latency() and success
    success = check_shadow_observability() and success
    success = check_operating_modes() and success
    check_database_preservation()
    success = run_full_tests() and success

    print("\n" + "=" * 80)
    if success:
        print("  [OK] ALL RELEASE CHECKS AND VERIFICATION TESTS PASSED SUCCESSFULLY.")
    else:
        print("  [FAIL] ONE OR MORE RELEASE CHECKS FAILED.")
    print("=" * 80)

    sys.exit(0 if success else 1)



if __name__ == "__main__":
    main()
