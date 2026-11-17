"""Automated and Interactive Demonstration Walkthrough for SentinelX-Shift.

Executes the 10-step Mode 2 replica defense walkthrough, verifying
isolation, honeypot decoy detection, anti-spoofing, and review DB preservation.
"""

import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.demo_hod import run_demo_walkthrough

if __name__ == "__main__":
    run_demo_walkthrough()
