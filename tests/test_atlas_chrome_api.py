"""HTTP smoke for Atlas chrome APIs: workspace list/use/add + ingest path."""
from __future__ import annotations

import json
import os
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

os.environ.setdefault("OKBAY_WORKSPACE", str(Path("/tmp/okbay-chrome-ws")))
os.environ.setdefault("XDG_STATE_HOME", str(Path("/tmp/okbay-chrome-state")))
os.environ.setdefault("XDG_CONFIG_HOME", str(Path("/tmp/okbay-chrome-config")))


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    work = tmp_path / "home" / "Work"
    work.mkdir(parents=True)
    hub = work / "okbay"
    bio = work / "biocure"
    bio.mkdir()
    (bio / "wiki").mkdir()
    (bio / "vault").mkdir()
    monkeypatch.setenv("OKBAY_WORKSPACE", str(hub))
    monkeypatch.setenv("OKBAY_WORK_ROOT", str(work))

    from okbay import paths, workroot
    from okbay.server import Handler
    from http.server import ThreadingHTTPServer

    paths.ensure_workspace(hub)
    workroot.add_workspace("biocure", bio)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield {"port": port, "bio": bio, "hub": hub}
    httpd.shutdown()


def _req(port, method, path, body=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    payload = None
    headers = {}
    if body is not None:
        payload = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(payload))
    conn.request(method, path, body=payload, headers=headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()
    return res.status, json.loads(data.decode() or "{}")


def test_workspace_list_use_add(server):
    port = server["port"]
    status, doc = _req(port, "GET", "/api/workspace/list")
    assert status == 200
    assert "biocure" in doc["workspaces"]
    assert "okbay" in doc["workspaces"]

    status, used = _req(port, "POST", "/api/workspace/use", {"name": "biocure"})
    assert status == 200
    assert used.get("ok") is True
    assert used.get("name") == "biocure"

    status, listed = _req(port, "GET", "/api/workspace")
    assert status == 200
    assert listed.get("active") == "biocure"

    extra = server["hub"].parent / "extra-ws"
    status, added = _req(port, "POST", "/api/workspace/add", {
        "name": "extra",
        "path": str(extra),
    })
    assert status == 200
    assert added.get("ok") is True
    status, listed2 = _req(port, "GET", "/api/workspace/list")
    assert "extra" in listed2["workspaces"]


def test_atlas_static_and_ingest(server, tmp_path):
    port = server["port"]
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/atlas")
    res = conn.getresponse()
    html = res.read().decode()
    conn.close()
    assert res.status == 200
    assert 'id="edge-mode"' in html
    assert 'id="ingest-add"' in html
    assert 'id="workspace-switch"' in html
    assert "classic-graph.js" in html

    for asset in (
        "/static/atlas-chrome.js",
        "/static/classic-graph.js",
        "/static/vendor/d3.min.js",
        "/static/vendor/knowledge-atlas.js",
    ):
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", asset)
        res = conn.getresponse()
        body = res.read()
        conn.close()
        assert res.status == 200, asset
        assert len(body) > 100, asset

    note = tmp_path / "drop.txt"
    note.write_text("hello atlas chrome ingest\n", encoding="utf-8")
    status, doc = _req(port, "POST", "/api/ingest", {"path": str(note)})
    assert status == 200
    assert doc.get("ok") is True or doc.get("needs_confirm") is True or "stem" in doc


def test_chrome_js_has_keybinds():
    chrome = Path(__file__).resolve().parents[1] / "src/okbay/static/atlas-chrome.js"
    src = chrome.read_text(encoding="utf-8")
    for needle in (
        "cycleEdgeMode",
        "promptAndIngest",
        "Workspace.toggle",
        "toggleMinimap",
        "Help.toggle",
        "lower === 'e'",
        "lower === 'v'",
        "lower === 'i'",
        "lower === 'o'",
        "lower === 'm'",
    ):
        assert needle in src, needle
