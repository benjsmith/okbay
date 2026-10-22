"""Atlas must not leave the entry node highlighted when nothing is focused."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE_TEST = Path(__file__).resolve().parent / "test_atlas_entry_highlight.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_atlas_entry_node_not_stuck_highlighted():
    proc = subprocess.run(["node", str(NODE_TEST)], cwd=str(ROOT),
                          capture_output=True, text=True, check=False, timeout=60)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok — atlas entry highlight" in proc.stdout
