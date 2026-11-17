"""Tests for SentinelX FastAPI service and CLI interface.

Verifies:
1. Service health check endpoint contract.
2. POST /api/v1/score contract and response schema.
3. Input validation error handling (HTTP 400 for malformed flow data).
4. CLI commands (--output json, --output table, --output-file).
5. CLI error handling on invalid files.
"""

import json
from pathlib import Path
import pytest
import pandas as pd
from fastapi import HTTPException

from src.api.service import app, health_check, score_flows, ScoreRequest
from src.alerts.schema import AlertResponse, RiskTier
from src.api.cli import main as cli_main, load_input_file, format_table


@pytest.fixture(scope="module")
def sample_flows_records():
    sample_path = Path("scratch/sample_flows.csv")
    if not sample_path.exists():
        df = pd.read_parquet("data/processed/cicids2017_sample60k.parquet")
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        df.head(10).to_csv(sample_path, index=False)
    df = pd.read_csv(sample_path)
    return df.head(3).to_dict(orient="records")


def test_api_health_endpoint():
    """GET /health returns expected operational metadata."""
    res = health_check()
    assert res["status"] == "healthy"
    assert res["service"] == "sentinelx-guard"
    assert res["guard_mode"] == "MONITOR_ONLY"
    assert res["autonomous_blocking"] is False
    assert res["feature_count"] == 76
    assert "sentinelx_lofo" in res["loaded_model"]


def test_api_score_flows_valid(sample_flows_records):
    """POST /api/v1/score returns schema-validated AlertResponse."""
    req = ScoreRequest(
        flows=sample_flows_records,
        signals=[
            {"request_rate": 100.0, "auth_failures": 5},
            None,
            {"waf_alert": True}
        ]
    )
    response = score_flows(req)
    assert isinstance(response, AlertResponse)
    assert response.total_flows == 3
    assert response.alerts_generated == 3
    assert response.guard_mode == "MONITOR_ONLY"
    assert response.alerts[0].autonomous_blocking_authorized is False
    assert response.alerts[0].confirming_signals["request_rate"].confirmed is True


def test_api_score_flows_validation_error():
    """Invalid or missing columns raise HTTP 400 Bad Request."""
    invalid_records = [{"Flow Duration": 100.0, "Invalid Feature": 1.0}]
    req = ScoreRequest(flows=invalid_records)

    with pytest.raises(HTTPException) as exc_info:
        score_flows(req)
    assert exc_info.value.status_code == 400
    assert "Invalid flow data" in exc_info.value.detail


def test_api_routes_registered():
    """Verifies that OpenAPI routes are properly declared on FastAPI app."""
    route_paths = [route.path for route in app.routes]
    assert "/health" in route_paths
    assert "/api/v1/health" in route_paths
    assert "/api/v1/score" in route_paths


def test_cli_table_formatting(sample_flows_records):
    """CLI table formatter produces expected column headers and structure."""
    req = ScoreRequest(flows=sample_flows_records)
    resp = score_flows(req)
    table_str = format_table(resp)

    assert "SENTINELX GUARD ALERT SUMMARY" in table_str
    assert "Flow ID" in table_str
    assert "Prod Score" in table_str
    assert "Tier" in table_str
    assert "Action" in table_str


def test_cli_execution_table(capsys):
    """CLI execution with --output table prints formatted summary."""
    ret = cli_main(["--file", "scratch/sample_flows.csv", "--output", "table"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "SENTINELX GUARD ALERT SUMMARY" in captured.out
    assert "MONITOR_ONLY" in captured.out


def test_cli_execution_json(capsys):
    """CLI execution with --output json outputs valid JSON payload."""
    ret = cli_main(["--file", "scratch/sample_flows.csv", "--output", "json"])
    assert ret == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert "alerts" in parsed
    assert parsed["guard_mode"] == "MONITOR_ONLY"
    assert len(parsed["alerts"]) > 0


def test_cli_output_file(tmp_path):
    """CLI --output-file correctly writes JSON to specified path."""
    out_file = tmp_path / "alerts_out.json"
    ret = cli_main([
        "--file", "scratch/sample_flows.csv",
        "--output", "json",
        "--output-file", str(out_file)
    ])
    assert ret == 0
    assert out_file.exists()
    content = json.loads(out_file.read_text(encoding="utf-8"))
    assert content["total_flows"] == 10


def test_cli_missing_file_error(capsys):
    """CLI with nonexistent file returns code 1 and writes error to stderr."""
    ret = cli_main(["--file", "nonexistent_file_path.csv"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "Error loading input file" in captured.err
