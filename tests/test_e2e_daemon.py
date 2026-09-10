"""Daemon smoke: python serve health + status."""
from pathlib import Path
import os, socket, subprocess, sys, time, json, urllib.request
import pytest

ROOT = Path(__file__).resolve().parents[1]

def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

@pytest.fixture
def serve(tmp_path, monkeypatch):
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    port = _free_port()
    proc = subprocess.Popen([sys.executable, "-m", "okbay", "serve", "--port", str(port)], cwd=str(ROOT), env=os.environ.copy())
    base = f"http://127.0.0.1:{port}"
    for _ in range(40):
        try:
            urllib.request.urlopen(base + "/health", timeout=0.2)
            break
        except Exception:
            time.sleep(0.05)
    yield base
    proc.terminate()

def test_status_json(serve):
    raw = urllib.request.urlopen(serve + "/api/status", timeout=3).read()
    body = json.loads(raw)
    assert "api_url" in body or "state" in body
