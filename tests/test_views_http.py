"""HTTP smoke for /api/views and sandboxed /views/<id>."""
from __future__ import annotations
from pathlib import Path
import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from okbay import paths, server, views


@pytest.fixture()
def httpd(tmp_path, monkeypatch):
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws"))
    paths.ensure_workspace(tmp_path / "ws")
    # Bind ephemeral port
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield port
    httpd.shutdown()


def test_views_http_roundtrip(httpd):
    port = httpd
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/api/views")
    res = conn.getresponse()
    body = json.loads(res.read().decode())
    assert res.status == 200
    assert body.get("ok") is True
    assert any(v["id"] == "atlas" for v in body["views"])

    payload = json.dumps({"id": "jit-deck", "title": "JIT", "html": "<p>deck</p>"})
    conn.request("POST", "/api/views", body=payload, headers={"Content-Type": "application/json"})
    res = conn.getresponse()
    body = json.loads(res.read().decode())
    assert res.status == 200 and body.get("ok") is True

    conn.request("GET", "/views/jit-deck")
    res = conn.getresponse()
    html = res.read().decode()
    assert res.status == 200
    assert "deck" in html
    assert res.getheader("Content-Security-Policy")

    conn.request("DELETE", "/api/views/jit-deck")
    res = conn.getresponse()
    body = json.loads(res.read().decode())
    assert res.status == 200 and body.get("ok") is True
    conn.close()
