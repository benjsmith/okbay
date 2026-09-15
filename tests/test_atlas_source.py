"""Vault source API: path sandbox + happy path for Viewer source mode."""
from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

import pytest

from okbay import paths, server, wiki


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    paths.ensure_workspace(root)
    monkeypatch.setenv("OKBAY_WORKSPACE", str(root))
    vault = paths.vault(root)
    (vault / "hello.md").write_text(
        "# Hello\n\nBody with **bold** and [[linked-page]].\n",
        encoding="utf-8",
    )
    (vault / "plain.txt").write_text("plain vault text\n", encoding="utf-8")
    # Outside vault (should never be readable via API).
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "passwd").write_text("nope\n", encoding="utf-8")
    return root, secrets


def test_safe_vault_file_happy_and_reject(ws):
    root, secrets = ws
    hit = wiki.safe_vault_file("hello.md", ws=root)
    assert hit is not None
    assert hit.name == "hello.md"

    assert wiki.safe_vault_file("../secrets/passwd", ws=root) is None
    assert wiki.safe_vault_file(str(secrets / "passwd"), ws=root) is None
    assert wiki.safe_vault_file("/etc/passwd", ws=root) is None
    assert wiki.safe_vault_file("vault/../../../etc/passwd", ws=root) is None


def test_source_payload_markdown(ws):
    root, _ = ws
    doc = wiki.source_payload(path="hello.md", ws=root)
    assert doc is not None
    assert doc["kind"] == "source"
    assert "Hello" in doc["title"] or doc["title"]
    assert "<strong>bold</strong>" in doc["body_html"]
    assert 'data-page="linked-page"' in doc["body_html"]
    assert doc["relpath"] == "hello.md"


def test_source_payload_traversal_raises(ws):
    root, _ = ws
    with pytest.raises(ValueError, match="traversal"):
        wiki.source_payload(path="../../etc/passwd", ws=root)


@pytest.fixture()
def httpd(ws, monkeypatch):
    root, _ = ws
    monkeypatch.setenv("OKBAY_WORKSPACE", str(root))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield port, root
    httpd.shutdown()


def _get(port: int, path: str):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    res = conn.getresponse()
    body = res.read().decode()
    conn.close()
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = body
    return res.status, data


def test_http_source_happy(httpd):
    port, _ = httpd
    status, doc = _get(port, "/api/atlas/source?path=hello.md")
    assert status == 200
    assert doc["kind"] == "source"
    assert "bold" in doc["body_html"]

    status, doc = _get(port, "/api/atlas/source?source=plain.txt")
    assert status == 200
    assert "plain vault text" in doc["markdown"]
    assert "<pre" in doc["body_html"]


def test_http_source_sandbox(httpd, ws):
    port, _ = httpd
    _, secrets = ws
    status, doc = _get(port, "/api/atlas/source?path=" + quote("../../etc/passwd"))
    assert status == 400
    assert "traversal" in doc.get("error", "").lower() or "reject" in doc.get("error", "").lower()

    status, doc = _get(port, "/api/atlas/source?path=" + quote(str(secrets / "passwd")))
    assert status in (400, 404)

    status, doc = _get(port, "/api/atlas/source?path=missing-nope.md")
    assert status == 404
