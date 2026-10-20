#!/usr/bin/env python
"""
scripts/run_dev.py — Forwarder to root run_dev.py
"""
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
run_dev = repo_root / "run_dev.py"

if __name__ == "__main__":
    import runpy
    sys.path.insert(0, str(repo_root))
    runpy.run_path(str(run_dev), run_name="__main__")

