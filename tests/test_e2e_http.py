"""HTTP contract e2e against python -m okbay serve."""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close(); return port

def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=3) as r:
        return r.status, json.loads(r.read())

@pytest.fixture(scope="module")
def daemon(tmp_path_factory):
    ws = tmp_path_factory.mktemp("ws"); state = tmp_path_factory.mktemp("state")
    (ws / "wiki").mkdir(); (ws / "vault").mkdir(); (ws / ".okbay").mkdir()
    (ws / "wiki" / "lease.md").write_text("---\nstem: lease\ntitle: Lease\nkind: source\n---\n\nTwo months deposit.\n")
    port = _free_port()
    env = os.environ.copy()
    env["OKBAY_WORKSPACE"] = str(ws)
    env["XDG_STATE_HOME"] = str(state)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.Popen([sys.executable, "-m", "okbay", "serve", "--host", "127.0.0.1", "--port", str(port)], env=env, cwd=str(ROOT))
    base = f"http://127.0.0.1:{port}"
    for _ in range(30):
        try:
            _get(base, "/health"); break
        except Exception:
            time.sleep(0.1)
    yield base, ws
    proc.terminate()

def test_health(daemon):
    base, _ = daemon
    code, body = _get(base, "/health")
    assert code == 200 and body.get("ok") is True

def test_search(daemon):
    base, _ = daemon
    code, body = _get(base, "/api/search?q=deposit")
    assert code == 200
    assert body.get("count", 0) >= 1 or body.get("hits")
