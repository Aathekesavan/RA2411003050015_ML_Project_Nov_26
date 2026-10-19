"""Report and Sidecar Generation Utilities for SentinelX-Shift.

Provides unified Git metadata extraction, run ID stamping, markdown formatting,
and .source_values.json sidecar generation to guarantee mathematical traceability.
"""

from typing import Dict, List, Optional, Tuple, Any, Set
import subprocess
import datetime
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd


def get_git_info() -> Tuple[str, str]:
    """Retrieve Git commit hash (stamped with -dirty if modified) and date-based run ID."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        ghash = res.stdout.strip()
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        if status_res.stdout.strip():
            ghash += "-dirty"
    except Exception:
        ghash = "unknown"

    date_str = datetime.datetime.now().strftime("%Y%m%d")
    clean_hash = ghash.replace("-dirty", "")
    run_id = f"run_{date_str}_{clean_hash}"
    return ghash, run_id


def extract_numbers_from_text(text: str) -> List[float]:
    """Extract all distinct numeric tokens from text as floats."""
    raw_nums = re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", text)
    valid_nums = []
    for s in raw_nums:
        try:
            val = float(s)
            valid_nums.append(val)
        except ValueError:
            continue
    return valid_nums


def format_markdown_table(df: pd.DataFrame) -> str:
    """Format DataFrame as markdown table without external dependencies."""
    headers = list(df.columns)
    lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        row_str = " | ".join(str(row[c]) for c in headers)
        lines.append(f"| {row_str} |")
    return "\n".join(lines)


def save_report_with_sidecar(
    md_path: Path,
    content: str,
    df: Optional[pd.DataFrame] = None,
    extra_values: Optional[List[Any]] = None
) -> Path:
    """Write markdown file and generate accompanying .source_values.json sidecar."""
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(content, encoding="utf-8")

    all_nums: Set[float] = set()

    # Extract numbers from DataFrame
    if df is not None:
        for col in df.columns:
            for val in df[col]:
                extracted = extract_numbers_from_text(str(val))
                all_nums.update(extracted)

    # Extract extra values
    if extra_values:
        for item in extra_values:
            extracted = extract_numbers_from_text(str(item))
            all_nums.update(extracted)

    # Extract numbers from markdown text content
    all_nums.update(extract_numbers_from_text(content))

    sidecar_data = {
        "source_file": md_path.name,
        "generated_at": datetime.datetime.now().isoformat(),
        "total_numbers_recorded": len(all_nums),
        "source_numbers": sorted(list(all_nums)),
        "data": df.to_dict(orient="records") if df is not None else [],
    }

    sidecar_path = md_path.with_suffix(".source_values.json")
    sidecar_path.write_text(json.dumps(sidecar_data, indent=2), encoding="utf-8")
    return sidecar_path
