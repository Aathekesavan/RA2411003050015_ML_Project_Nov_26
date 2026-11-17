"""Command-Line Interface (CLI) for SentinelX-Shift Guard.

Usage:
  sentinelx-scan --file <path_to_flows.csv> [--output json|table] [--output-file <path>]
  python -m src.api.cli --file <path_to_flows.csv>
"""

import sys
import argparse
import json
import logging
from pathlib import Path
import pandas as pd

from src.guard.engine import SentinelGuard, FlowValidationError
from src.alerts.schema import AlertResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sentinelx-scan")


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        prog="sentinelx-scan",
        description="SentinelX-Shift Network Flow Analysis and Alert Prioritization CLI"
    )
    parser.add_argument(
        "--file", "-f",
        required=True,
        type=str,
        help="Path to network flows file (.csv, .parquet, or .json)"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["json", "table"],
        default="json",
        help="Output format: 'json' (schema-validated JSON alerts) or 'table' (summary table)"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Optional destination file path to save output"
    )
    parser.add_argument(
        "--model-path", "-m",
        type=str,
        default=None,
        help="Optional path to model artifact .joblib file"
    )
    parser.add_argument(
        "--tau",
        type=float,
        default=None,
        help="Optional activation threshold override"
    )
    parser.add_argument(
        "--gamma",
        type=float,
        default=None,
        help="Optional boost magnitude override"
    )
    return parser.parse_args(args)


def load_input_file(filepath: Path) -> pd.DataFrame:
    """Load flows from CSV, Parquet, or JSON file."""
    if not filepath.exists():
        raise FileNotFoundError(f"Input file not found: {filepath}")

    suffix = filepath.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(filepath)
    elif suffix in [".parquet", ".pq"]:
        return pd.read_parquet(filepath)
    elif suffix == ".json":
        return pd.read_json(filepath)
    else:
        raise ValueError(f"Unsupported file format '{suffix}'. Supported formats: .csv, .parquet, .json")


def format_table(response: AlertResponse) -> str:
    """Format alert response as human-readable terminal table."""
    lines = [
        "=" * 105,
        f"SENTINELX GUARD ALERT SUMMARY | Model: {response.model_family} | Mode: {response.guard_mode}",
        f"Total Flows: {response.total_flows} | Alerts: {response.alerts_generated} | High Priority: {response.high_priority_count} | Latency: {response.execution_time_ms:.2f} ms",
        "=" * 105,
        f"{'Flow ID':<18} | {'Prod Score':<10} | {'AE Score':<9} | {'XGB Score':<9} | {'Tier':<8} | {'Action':<19} | {'Suspected Family'}",
        "-" * 105,
    ]
    for alert in response.alerts:
        flow_id = (alert.flow_id or "N/A")[:17]
        prod_s = f"{alert.scores.production_score:.4f}"
        ae_s = f"{alert.scores.autoencoder_score:.4f}"
        xgb_s = f"{alert.scores.supervised_score:.4f}"
        tier = alert.risk_tier.value
        action = alert.recommended_action.value
        fam = alert.suspected_family or "Benign / Unknown"
        lines.append(f"{flow_id:<18} | {prod_s:<10} | {ae_s:<9} | {xgb_s:<9} | {tier:<8} | {action:<19} | {fam}")
    lines.append("=" * 105)
    return "\n".join(lines)


def main(argv=None) -> int:
    args = parse_args(argv)
    input_path = Path(args.file)

    try:
        df = load_input_file(input_path)
    except Exception as e:
        sys.stderr.write(f"Error loading input file '{input_path}': {e}\n")
        return 1

    try:
        guard = SentinelGuard(
            model_path=args.model_path,
            tau=args.tau if args.tau is not None else 0.56,
            gamma=args.gamma if args.gamma is not None else 0.41,
        )
        response = guard.analyze_flows(flows=df)
    except FlowValidationError as e:
        sys.stderr.write(f"Flow validation error: {e}\n")
        return 1
    except Exception as e:
        sys.stderr.write(f"Inference error: {e}\n")
        return 1

    if args.output == "json":
        output_str = response.model_dump_json(indent=2)
    else:
        output_str = format_table(response)

    if args.output_file:
        out_p = Path(args.output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        logger.info(f"Results written to {out_p}")
    else:
        print(output_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())
