"""Run Node unit tests for atlas keyboard helpers (spatial / angular)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPERS = ROOT / "src" / "okbay" / "static" / "atlas-keys-helpers.js"
NODE_TEST = Path(__file__).resolve().parent / "test_atlas_key_helpers.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_atlas_key_helpers_mjs():
    assert HELPERS.is_file()
    assert NODE_TEST.is_file()
    proc = subprocess.run(
        ["node", str(NODE_TEST)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok — atlas key helpers" in proc.stdout
