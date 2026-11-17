"""FastAPI service for SentinelX-Shift Guard scoring, alert generation, and analyst review queue.

Endpoints:
- POST /api/v1/score: Analyze network flows and return schema-validated alerts.
- GET /api/v1/alerts: Query prioritized alert queue with filters.
- GET /api/v1/alerts/{alert_id}: Retrieve detailed alert telemetry and signals.
- POST /api/v1/alerts/{alert_id}/review: Record analyst review action.
- POST /api/v1/queue/load_sample: Load sample flows into active queue.
- GET /health: Health check and service metadata.
- GET /dashboard: Serves interactive HTML dashboard.
"""

from typing import Dict, List, Optional, Any, Union
import logging
from pathlib import Path
import os
from fastapi import FastAPI, HTTPException, status, Query, Path as FastPath, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.alerts.schema import (
    AlertResponse,
    QueueResponse,
    QueueAlert,
    ReviewStatus,
    ReviewAction,
    ReviewRecord,
)
from src.alerts.store import LocalReviewStore
from src.guard.engine import SentinelGuard, FlowValidationError
from src.enforcement.models import (
    OperatingMode,
    EnforcementAction,
    EnforcementStatus,
    GlobalEnforcementConfig,
    SiteConfig,
    ActiveBlock,
    EnforcementDecision,
)
from src.enforcement.policy import get_default_enforcement_engine
from src.replica.app import replica_router, get_replica_adapter
from src.replica.honeypot import get_honeypot_events
from src.replica.scenarios import (
    run_replica_bruteforce_scenario,
    run_replica_benign_burst_scenario,
    run_replica_honeypot_scenario,
)
from src.replica.counterfactual import (
    get_counterfactual_comparison,
    reset_demo_scenario,
)

logger = logging.getLogger(__name__)

# Singletons
_guard_instance: Optional[SentinelGuard] = None
_store_instance: Optional[LocalReviewStore] = None


def get_guard(model_path: Optional[str] = None) -> SentinelGuard:
    """Get or create singleton SentinelGuard instance."""
    global _guard_instance
    if _guard_instance is None or model_path is not None:
        _guard_instance = SentinelGuard(model_path=model_path)
    return _guard_instance


def get_store() -> LocalReviewStore:
    """Get or create singleton LocalReviewStore instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = LocalReviewStore()
    return _store_instance


app = FastAPI(
    title="SentinelX-Shift Guard API & Analyst Review Queue",
    description="Operational intrusion detection, alert prioritization, and triage dashboard service",
    version="2.0.0",
)
app.include_router(replica_router)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Render authentic institutional 403 HTML page for browser requests to blocked replica routes."""
    if exc.status_code == 403 and "text/html" in request.headers.get("accept", ""):
        if isinstance(exc.detail, dict) and exc.detail.get("status") == "REPLICA_BLOCKED":
            from src.replica.html_views import render_replica_blocked_page
            return HTMLResponse(content=render_replica_blocked_page(exc.detail), status_code=403)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


class ScoreRequest(BaseModel):
    """Request payload for flow scoring."""
    flows: Union[List[Dict[str, Any]], Dict[str, Any]] = Field(
        ...,
        description="Single flow record or list of flow records with 76 behavioral features"
    )
    signals: Optional[Union[List[Optional[Dict[str, Any]]], Dict[str, Any]]] = Field(
        None,
        description="Optional independent confirming signal metadata (request_rate, auth_failures, waf_alert, etc.)"
    )
    model_path: Optional[str] = Field(
        None,
        description="Optional custom path to model artifact"
    )
    tau: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Optional override for supervised activation threshold tau"
    )
    gamma: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Optional override for boost magnitude gamma"
    )
    persist_to_queue: bool = Field(
        True,
        description="Whether to automatically add generated alerts to the local review queue"
    )
    batch_id: Optional[str] = Field(
        None,
        description="Optional batch or ingestion run identifier"
    )
    site_id: Optional[str] = Field(
        None,
        description="Optional site identifier for Mode 1 or Mode 2 enforcement evaluation"
    )
    enforce_policy: bool = Field(
        False,
        description="Whether to evaluate backend per-site blocking policy (default: False)"
    )


class CorrelateAndScoreRequest(BaseModel):
    """Request payload for flow scoring with web log and WAF correlation."""
    flows: Union[List[Dict[str, Any]], Dict[str, Any]] = Field(
        ...,
        description="Single flow record or list of flow records with features and optional source_ip / timestamp"
    )
    access_logs: Optional[str] = Field(None, description="Raw text of Nginx access logs")
    error_logs: Optional[str] = Field(None, description="Raw text of Nginx error logs")
    waf_logs: Optional[str] = Field(None, description="Raw text of ModSecurity WAF events or JSON")
    time_window_seconds: float = Field(30.0, ge=1.0, le=3600.0, description="Temporal correlation window in seconds")
    model_path: Optional[str] = Field(None, description="Optional custom path to model artifact")
    tau: Optional[float] = Field(None, ge=0.0, le=1.0, description="Activation threshold tau")
    gamma: Optional[float] = Field(None, ge=0.0, le=1.0, description="Boost magnitude gamma")
    persist_to_queue: bool = Field(True, description="Whether to persist generated alerts to review queue")
    batch_id: Optional[str] = Field(None, description="Optional batch identifier")
    site_id: Optional[str] = Field(None, description="Optional site identifier for Mode 1 or Mode 2 enforcement evaluation")
    enforce_policy: bool = Field(False, description="Whether to evaluate backend per-site blocking policy (default: False)")


class ShadowReplayRequest(BaseModel):
    """Request payload for running a shadow replay."""
    dataset_source: str = Field("synthetic", description="Source: 'synthetic', 'sample_flows', or 'benchmark'")
    batch_size: int = Field(10, ge=1, le=1000)
    max_flows: int = Field(50, ge=1, le=5000)
    include_logs: bool = Field(True, description="Whether to correlate synthetic web/WAF logs")


class ShadowIngestRequest(BaseModel):
    """Request payload for shadow-mode flow evaluation."""
    flows: Union[List[Dict[str, Any]], Dict[str, Any]] = Field(..., description="Flow records to evaluate in shadow mode")
    access_logs: Optional[str] = Field(None, description="Optional Nginx access log string")
    error_logs: Optional[str] = Field(None, description="Optional Nginx error log string")
    waf_logs: Optional[str] = Field(None, description="Optional ModSecurity WAF events string")
    time_window_seconds: float = Field(30.0, ge=1.0, le=3600.0)
    persist_alerts_to_queue: bool = Field(False, description="Whether to persist alerts to review queue")




class ReviewActionRequest(BaseModel):
    """Request payload for recording an analyst triage decision."""
    action: ReviewAction = Field(..., description="Triage action to apply")
    analyst_id: str = Field("analyst-1", description="Identifier of the reviewing analyst")
    notes: Optional[str] = Field(None, description="Investigation notes or rationale")


@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
def health_check():
    """Service health and operational status."""
    guard = get_guard()
    store = get_store()
    stats = store.get_queue_statistics()
    enforcement = get_default_enforcement_engine()
    return {
        "status": "healthy",
        "service": "sentinelx-guard",
        "version": "2.0.0",
        "guard_mode": "MONITOR_ONLY" if not enforcement.config.global_blocking_enabled else "DEFENSIVE_MONITORING",
        "operating_mode": enforcement.config.operating_mode.value,
        "global_blocking_enabled": enforcement.config.global_blocking_enabled,
        "emergency_stop_active": enforcement.config.emergency_stop_active,
        "autonomous_blocking": False if not enforcement.config.global_blocking_enabled else True,
        "active_blocks_count": len(enforcement.get_all_active_blocks()),
        "loaded_model": guard.model_path.name,
        "feature_count": len(guard.feature_cols),
        "production_tau": guard.tau,
        "production_gamma": guard.gamma,
        "queue_stats": stats,
    }


@app.post(
    "/api/v1/score",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    tags=["Scoring"]
)
def score_flows(request: ScoreRequest) -> AlertResponse:
    """Analyze network flows and return prioritized alerts.

    Applies Autoencoder-Anchored Gated Boost and evaluates independent confirming signals.
    Enforces monitor-and-recommend invariant (Defensive Principle 1).
    """
    try:
        guard = get_guard(model_path=request.model_path)
        if request.tau is not None:
            guard.tau = float(request.tau)
        if request.gamma is not None:
            guard.gamma = float(request.gamma)

        response = guard.analyze_flows(
            flows=request.flows,
            signals=request.signals,
            batch_id=request.batch_id,
            site_id=request.site_id,
            enforce_policy=request.enforce_policy,
        )

        if request.persist_to_queue and response.alerts:
            store = get_store()
            # Prepare telemetry dictionary list for detail view
            if isinstance(request.flows, dict):
                telemetry_list = [request.flows]
            else:
                telemetry_list = request.flows
            store.insert_alerts(response.alerts, telemetry_list=telemetry_list)

        return response

    except FlowValidationError as e:
        logger.error(f"Validation error in flow data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid flow data: {str(e)}"
        )
    except FileNotFoundError as e:
        logger.error(f"Model file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Unexpected error during flow inference")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(e)}"
        )


@app.get(
    "/api/v1/alerts",
    response_model=QueueResponse,
    status_code=status.HTTP_200_OK,
    tags=["Queue"]
)
def list_queue_alerts(
    risk_tier: Optional[str] = None,
    suspected_family: Optional[str] = None,
    review_status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> QueueResponse:
    """Query the prioritized alert queue with optional filters."""
    store = get_store()
    alerts, total_count = store.get_alerts(
        risk_tier=risk_tier,
        suspected_family=suspected_family,
        review_status=review_status,
        limit=limit,
        offset=offset
    )
    stats = store.get_queue_statistics()
    return QueueResponse(
        total_matching=total_count,
        returned_count=len(alerts),
        queue_stats=stats,
        alerts=alerts,
        guard_mode="MONITOR_ONLY"
    )


@app.get(
    "/api/v1/alerts/{alert_id}",
    response_model=QueueAlert,
    status_code=status.HTTP_200_OK,
    tags=["Queue"]
)
def get_alert_detail(
    alert_id: str = FastPath(..., description="Alert UUID")
) -> QueueAlert:
    """Retrieve detailed telemetry and confirming signals for a single alert."""
    store = get_store()
    alert = store.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID '{alert_id}' not found."
        )
    return alert


@app.post(
    "/api/v1/alerts/{alert_id}/review",
    response_model=ReviewRecord,
    status_code=status.HTTP_200_OK,
    tags=["Queue"]
)
def record_analyst_review(
    alert_id: str = FastPath(..., description="Alert UUID to review"),
    body: ReviewActionRequest = ...
) -> ReviewRecord:
    """Record an analyst triage action on an alert (Confirm, Mark Benign, Investigate, Escalate)."""
    store = get_store()
    try:
        record = store.record_review(
            alert_id=alert_id,
            action=body.action,
            analyst_id=body.analyst_id,
            notes=body.notes
        )
        return record
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception("Error recording review action")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post(
    "/api/v1/queue/load_sample",
    response_model=QueueResponse,
    status_code=status.HTTP_200_OK,
    tags=["Queue"]
)
def load_sample_alerts(
    force: bool = False,
    batch_id: str = "sample-batch-cicids2017-default"
) -> QueueResponse:
    """Load sample flows into the active queue for demonstration and triage.

    Idempotent by default: if a sample batch with `batch_id` already exists with
    PENDING status, returns the existing queue without adding duplicates.
    Use force=True to load a new sample run.
    """
    from datetime import datetime, timezone
    store = get_store()
    effective_batch_id = batch_id

    if force:
        effective_batch_id = f"sample-run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    elif store.has_pending_batch(effective_batch_id):
        logger.info(f"Sample batch '{effective_batch_id}' already has pending alerts; skipping duplicate load.")
        return list_queue_alerts()

    import pandas as pd
    sample_file = Path("scratch/sample_flows.csv")
    if not sample_file.exists():
        df_src = pd.read_parquet("data/processed/cicids2017_sample60k.parquet")
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        df_src.head(20).to_csv(sample_file, index=False)

    df = pd.read_csv(sample_file)
    records = df.head(15).to_dict(orient="records")

    # Add realistic confirming signals for some flows
    signals: List[Optional[Dict[str, Any]]] = []
    for i, rec in enumerate(records):
        label = str(rec.get("Label", ""))
        if "Patator" in label or "Brute" in label:
            signals.append({"request_rate": 85.0, "auth_failures": 12})
        elif "PortScan" in label:
            signals.append({"connection_attempts": 45, "request_rate": 60.0})
        elif "Web" in label:
            signals.append({"waf_alert": True, "http_status": 403})
        else:
            signals.append(None)

    req = ScoreRequest(
        flows=records,
        signals=signals,
        batch_id=effective_batch_id,
        persist_to_queue=True
    )
    _ = score_flows(req)

    return list_queue_alerts()


@app.post(
    "/api/v1/correlate_and_score",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    tags=["Inference & Ingestion"]
)
def correlate_and_score_flows(request: CorrelateAndScoreRequest) -> AlertResponse:
    """Correlate provided web server/WAF logs with flows, evaluate confirming signals, and score."""
    from src.ingestion.parsers import NginxAccessLogParser, NginxErrorLogParser, ModSecurityParser
    from src.ingestion.correlator import LogFlowCorrelator

    events = []
    if request.access_logs:
        events.extend(NginxAccessLogParser().parse(request.access_logs).events)
    if request.error_logs:
        events.extend(NginxErrorLogParser().parse(request.error_logs).events)
    if request.waf_logs:
        events.extend(ModSecurityParser().parse(request.waf_logs).events)

    correlator = LogFlowCorrelator(events=events, time_window_seconds=request.time_window_seconds)

    if isinstance(request.flows, dict):
        flows_list = [request.flows]
    else:
        flows_list = request.flows

    signals_list, _ = correlator.correlate_batch(flows_list)

    score_req = ScoreRequest(
        flows=flows_list,
        signals=signals_list,
        model_path=request.model_path,
        tau=request.tau,
        gamma=request.gamma,
        persist_to_queue=request.persist_to_queue,
        batch_id=request.batch_id,
        site_id=request.site_id,
        enforce_policy=request.enforce_policy,
    )
    return score_flows(score_req)


@app.post(
    "/api/v1/demo/phase3",
    response_model=QueueResponse,
    status_code=status.HTTP_200_OK,
    tags=["Demo"]
)
def run_phase3_demo_endpoint(
    force: bool = False,
    batch_id: str = "phase3-demo-run"
) -> QueueResponse:
    """Execute the Phase 3 web-server and WAF log correlation demo and return the updated queue."""
    from scripts.demo_phase3 import run_phase3_demo
    from datetime import datetime, timezone
    store = get_store()
    effective_batch_id = batch_id
    if force:
        effective_batch_id = f"phase3-demo-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    elif store.has_pending_batch(effective_batch_id):
        logger.info(f"Phase 3 demo batch '{effective_batch_id}' already has pending alerts; returning queue.")
        return list_queue_alerts()

    _ = run_phase3_demo(persist_to_store=True, batch_id=effective_batch_id)
    return list_queue_alerts()


# ---------------------------------------------------------------------------
# Shadow Mode & Observability Endpoints (Phase 5)
# ---------------------------------------------------------------------------

_shadow_evaluator_instance = None


def get_shadow_evaluator():
    """Get or create singleton ShadowEvaluator."""
    global _shadow_evaluator_instance
    if _shadow_evaluator_instance is None:
        from src.observability.engine import ShadowEvaluator
        _shadow_evaluator_instance = ShadowEvaluator(guard=get_guard(), review_store=get_store())
    return _shadow_evaluator_instance


@app.post(
    "/api/v1/shadow/ingest",
    status_code=status.HTTP_200_OK,
    tags=["Shadow Mode & Observability"]
)
def shadow_ingest_flows(req: ShadowIngestRequest):
    """Evaluate flow batch in passive shadow mode and record operational metrics."""
    from src.ingestion.parsers import NginxAccessLogParser, NginxErrorLogParser, ModSecurityParser
    evaluator = get_shadow_evaluator()
    events = []
    if req.access_logs:
        events.extend(NginxAccessLogParser().parse(req.access_logs).events)
    if req.error_logs:
        events.extend(NginxErrorLogParser().parse(req.error_logs).events)
    if req.waf_logs:
        events.extend(ModSecurityParser().parse(req.waf_logs).events)

    snap = evaluator.evaluate_batch(
        flows=req.flows,
        logs=events,
        time_window_seconds=req.time_window_seconds,
        is_replay=False,
        run_source="shadow_api_ingest",
        persist_alerts_to_queue=req.persist_alerts_to_queue
    )
    return snap.model_dump()


@app.post(
    "/api/v1/shadow/replay",
    status_code=status.HTTP_200_OK,
    tags=["Shadow Mode & Observability"]
)
def shadow_replay(req: ShadowReplayRequest):
    """Execute shadow replay run over synthetic or approved sample data without network action."""
    from src.observability.replay import run_shadow_replay
    evaluator = get_shadow_evaluator()
    summary = run_shadow_replay(
        dataset_source=req.dataset_source,
        batch_size=req.batch_size,
        max_flows=req.max_flows,
        include_logs=req.include_logs,
        evaluator=evaluator
    )
    return summary


@app.get(
    "/api/v1/shadow/metrics",
    status_code=status.HTTP_200_OK,
    tags=["Shadow Mode & Observability"]
)
def get_shadow_metrics():
    """Retrieve the latest operational observability snapshot."""
    from src.observability.replay import run_shadow_replay
    evaluator = get_shadow_evaluator()
    latest = evaluator.metrics_store.get_latest_snapshot()
    if not latest:
        # Generate initial baseline snapshot via sample replay
        _ = run_shadow_replay(dataset_source="synthetic", max_flows=10, evaluator=evaluator)
        latest = evaluator.metrics_store.get_latest_snapshot()
    return latest.model_dump() if latest else {}


@app.post(
    "/api/v1/shadow/reset",
    status_code=status.HTTP_200_OK,
    tags=["Shadow Mode & Observability"]
)
def reset_shadow_metrics():
    """Safely reset shadow metrics snapshots and run history without altering analyst reviews."""
    evaluator = get_shadow_evaluator()
    pruned_count = evaluator.metrics_store.reset_metrics()
    return {"status": "SUCCESS", "reset_snapshots_count": pruned_count}


# ---------------------------------------------------------------------------
# Operating Modes & Enforcement Schemas and Endpoints
# ---------------------------------------------------------------------------

class UpdateGlobalConfigRequest(BaseModel):
    operating_mode: Optional[OperatingMode] = None
    global_blocking_enabled: Optional[bool] = None
    emergency_stop_active: Optional[bool] = None


class UpdateSiteConfigRequest(BaseModel):
    blocking_enabled: Optional[bool] = None
    trusted_allowlist: Optional[List[str]] = None
    block_ttl_seconds: Optional[int] = None


class ReleaseBlockRequest(BaseModel):
    target_ip: Optional[str] = None
    ip_address: Optional[str] = None

    def get_effective_ip(self) -> str:
        return self.target_ip or self.ip_address or ""


class RunReplicaScenarioRequest(BaseModel):
    scenario_name: Optional[str] = Field(None, description="'bruteforce', 'benign_burst', or 'honeypot'")
    scenario: Optional[str] = Field(None, description="Alias for scenario_name")

    def get_effective_name(self) -> str:
        return self.scenario or self.scenario_name or "bruteforce"


def require_local_or_admin(request: Request):
    """Security safeguard: Enforcement mutation endpoints are restricted to local localhost

    callers by default, or require a valid X-SentinelX-Admin-Key header if configured.
    This protects against unauthorized remote policy changes or DOS via emergency stop.
    """
    if request is None:
        return True

    admin_key = os.environ.get("SENTINELX_ADMIN_KEY")
    auth_header = request.headers.get("X-SentinelX-Admin-Key")
    if admin_key and auth_header == admin_key:
        return True

    client_host = request.client.host if request.client else "127.0.0.1"
    if client_host in ("127.0.0.1", "::1", "localhost", "testclient"):
        return True

    logger.warning(f"Unauthorized remote enforcement mutation attempt from client host: {client_host}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "FORBIDDEN_REMOTE_ENFORCEMENT_MUTATION",
            "message": "Enforcement mutation endpoints are restricted to local localhost requests.",
            "client_host": client_host,
            "remediation": "Submit requests from localhost loopback or configure SENTINELX_ADMIN_KEY.",
        }
    )


@app.get("/api/v1/enforcement/config", tags=["Operating Modes & Enforcement"])
def get_enforcement_config():
    """Get system enforcement configuration, emergency stop status, and per-site settings."""
    engine = get_default_enforcement_engine()
    return engine.config.model_dump()


@app.post("/api/v1/enforcement/config", dependencies=[Depends(require_local_or_admin)], tags=["Operating Modes & Enforcement"])
def update_enforcement_config(req: UpdateGlobalConfigRequest):
    """Update global blocking enable, emergency stop switch, or operating mode."""
    engine = get_default_enforcement_engine()
    if req.operating_mode is not None:
        engine.config.operating_mode = req.operating_mode
    if req.global_blocking_enabled is not None:
        engine.config.global_blocking_enabled = req.global_blocking_enabled
    if req.emergency_stop_active is not None:
        engine.config.emergency_stop_active = req.emergency_stop_active
    return engine.config.model_dump()


@app.post("/api/v1/enforcement/sites/{site_id}", dependencies=[Depends(require_local_or_admin)], tags=["Operating Modes & Enforcement"])
def update_site_config(site_id: str, req: UpdateSiteConfigRequest):
    """Update per-site blocking toggle, trusted allowlist, or TTL duration."""
    engine = get_default_enforcement_engine()
    site = engine.get_site_config(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")
    if req.blocking_enabled is not None:
        site.blocking_enabled = req.blocking_enabled
    if req.trusted_allowlist is not None:
        site.trusted_allowlist = req.trusted_allowlist
    if req.block_ttl_seconds is not None:
        site.block_ttl_seconds = req.block_ttl_seconds
    return site.model_dump()


@app.get("/api/v1/enforcement/blocks", tags=["Operating Modes & Enforcement"])
def list_active_blocks():
    """List all currently active temporary blocks across all adapters."""
    engine = get_default_enforcement_engine()
    blocks = engine.get_all_active_blocks()
    dumped = [b.model_dump() for b in blocks]
    return {
        "active_blocks_count": len(blocks),
        "count": len(blocks),
        "blocks": dumped,
        "active_blocks": dumped,
    }


@app.post("/api/v1/enforcement/blocks/release", dependencies=[Depends(require_local_or_admin)], tags=["Operating Modes & Enforcement"])
def release_active_block(req: ReleaseBlockRequest):
    """Manually release an active block before its TTL expires."""
    engine = get_default_enforcement_engine()
    ip = req.get_effective_ip()
    released = engine.release_block(ip)
    return {"released": released, "target_ip": ip, "ip_address": ip}


@app.get("/api/v1/enforcement/audit", tags=["Operating Modes & Enforcement"])
def get_enforcement_audit(limit: int = 50):
    """Retrieve recent enforcement decisions audit trail."""
    engine = get_default_enforcement_engine()
    dumped = [d.model_dump() for d in engine.audit_log[:limit]]
    return {
        "audit_count": len(dumped),
        "count": len(dumped),
        "records": dumped,
        "audit_trail": dumped,
    }


@app.post("/api/v1/replica/scenarios/run", dependencies=[Depends(require_local_or_admin)], tags=["Mode 2: Isolated Replica Lab"])
def run_replica_scenario_endpoint(req: RunReplicaScenarioRequest):
    """Execute a safe Mode 2 simulated scenario against the isolated replica."""
    engine = get_default_enforcement_engine()
    guard = get_guard()
    scen = req.get_effective_name()
    if scen == "bruteforce":
        res = run_replica_bruteforce_scenario(engine=engine, guard=guard)
    elif scen == "benign_burst":
        res = run_replica_benign_burst_scenario(engine=engine, guard=guard)
    elif scen == "honeypot":
        res = run_replica_honeypot_scenario(engine=engine, guard=guard)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{scen}'. Supported: 'bruteforce', 'benign_burst', 'honeypot'"
        )
    return {
        **res,
        "result": res,
    }


@app.get("/api/v1/replica/honeypot/events", tags=["Mode 2: Isolated Replica Lab"])
def list_honeypot_events(limit: int = 50):
    """Retrieve recent structured honeypot decoy trap events."""
    events = get_honeypot_events(limit=limit)
    return {
        "count": len(events),
        "events": [e.model_dump() for e in events],
    }


@app.get("/api/v1/replica/scenarios/comparison", tags=["Mode 2: Isolated Replica Lab"])
def get_scenario_comparison_endpoint(scenario_name: str = "bruteforce"):
    """Retrieve non-mutating side-by-side comparison of SentinelX protection vs.

    hypothetical unmitigated outcome using synthetic fake data.
    """
    return get_counterfactual_comparison(scenario_name=scenario_name)


@app.post("/api/v1/replica/scenarios/reset", dependencies=[Depends(require_local_or_admin)], tags=["Mode 2: Isolated Replica Lab"])
def reset_scenario_endpoint():
    """Reset active demo scenario blocks on the local replica adapter.

    Leaves review database and historical alerts completely untouched.
    """
    return reset_demo_scenario()


# Mount Static Files for Dashboard UI
dashboard_dir = Path("dashboard")
if dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")


@app.get("/", tags=["Dashboard"])
def root_redirect():
    """Redirect root path to interactive dashboard."""
    return RedirectResponse(url="/dashboard/")


@app.get("/presentation", tags=["Dashboard"])
def presentation_redirect():
    """Redirect to Mode 2 active-scenario presentation console."""
    return RedirectResponse(url="/dashboard/presentation.html")
