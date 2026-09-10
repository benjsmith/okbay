#!/usr/bin/env python3
"""Thin wrapper. The daemon lives in python -m okbay serve."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from okbay.server import serve
if __name__ == "__main__":
    serve()
