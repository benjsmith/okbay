"""Thin client / mapper over okstratr harness registry (SSOT)."""
from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from okbay import okstratr_harness, server


def _okstratr_list_payload(**overrides):
    base = {
        "ok": True,
        "path": "/tmp/harnesses.toml",
        "enabled": ["grok", "claude"],
        "preference": ["grok", "claude"],
        "defaults": {"adapter": "herdr", "backend": "herdr"},
        "backend": "herdr",
        "harnesses": [
            {
                "id": "grok",
                "label": "Grok",
                "herdr_kind": "grok",
                "enabled": True,
                "installed": True,
                "bin_names": ["grok"],
                "default_model": "grok-4.6",
                "models": ["grok-4.6", "grok-4"],
                "effort": {"trivial": "grok-4.6", "normal": "grok-4.6"},
                "settings": {"reasoning": "low"},
                "notes": "",
            },
            {
                "id": "claude",
                "label": "Claude",
                "herdr_kind": "claude",
                "enabled": True,
                "installed": False,
                "bin_names": ["claude"],
                "default_model": "claude-haiku",
                "models": ["claude-haiku"],
                "effort": {},
                "settings": {},
                "notes": "install claude",
            },
            {
                "id": "codex",
                "label": "Codex",
                "enabled": False,
                "installed": False,
                "default_model": "gpt-5",
                "models": ["gpt-5"],
                "effort": {},
                "settings": {},
                "notes": "",
            },
        ],
        "blackboard": {"duration_days": 3.0, "chip": "bb: 3d"},
    }
    base.update(overrides)
    return base


def test_normalize_registry_maps_rows():
    view = okstratr_harness.normalize_registry(_okstratr_list_payload())
    assert view["ok"] is True
    assert view["ssot"] == "okstratr"
    assert view["host"] == "okbay"
    assert view["enabled"] == ["grok", "claude"]
    assert view["backend"] == "herdr"
    assert len(view["harnesses"]) == 3
    grok = view["harnesses"][0]
    assert grok["id"] == "grok"
    assert grok["enabled"] is True
    assert grok["default_model"] == "grok-4.6"
    assert "grok-4.6" in grok["models"]
    assert view["daemon_paths"]["list"] == "/api/okstratr/harness"
    assert view["embed_paths"]["list"] == "/embed/okstratr/api/harness"
    assert view["blackboard"]["chip"] == "bb: 3d"


def test_normalize_skips_bad_rows_and_fills_defaults():
    view = okstratr_harness.normalize_registry(
        {
            "harnesses": [
                "nope",
                {"label": "missing id"},
                {"id": "pi", "enabled": 1, "models": "bad"},
            ]
        }
    )
    assert view["ssot"] == "okstratr"
    assert len(view["harnesses"]) == 1
    assert view["harnesses"][0]["id"] == "pi"
    assert view["harnesses"][0]["models"] == []
    assert view["harnesses"][0]["enabled"] is True


def test_normalize_none_is_empty_ssot_view():
    view = okstratr_harness.normalize_registry(None)
    assert view["ok"] is True
    assert view["ssot"] == "okstratr"
    assert view["harnesses"] == []
    assert view["enabled"] == []


def test_upstream_url_defaults(monkeypatch):
    monkeypatch.delenv("OKBAY_OKSTRATR_UPSTREAM", raising=False)
    assert okstratr_harness.upstream_url("list") == "http://127.0.0.1:8767/api/harness"
    assert (
        okstratr_harness.upstream_url("enable")
        == "http://127.0.0.1:8767/api/harness/enable"
    )


def test_upstream_url_rejects_non_loopback(monkeypatch):
    monkeypatch.setenv("OKBAY_OKSTRATR_UPSTREAM", "http://evil.example:8767")
    with pytest.raises(okstratr_harness.OkstratrHarnessError):
        okstratr_harness.upstream_url("list")


class _StubOkstratr(BaseHTTPRequestHandler):
    """Minimal mocked okstratr harness API."""

    state: dict | None = None
    seen: dict | None = None

    def log_message(self, fmt, *args):
        return

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        return json.loads(self.rfile.read(n).decode() or "{}")

    def do_GET(self):
        assert self.__class__.seen is not None
        self.__class__.seen["host"] = self.headers.get("X-Okstratr-Host", "")
        self.__class__.seen["path"] = self.path
        if self.path == "/api/harness":
            enabled = list((self.__class__.state or {}).get("enabled") or ["grok"])
            return self._json(_okstratr_list_payload(enabled=enabled))
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        assert self.__class__.seen is not None and self.__class__.state is not None
        self.__class__.seen["host"] = self.headers.get("X-Okstratr-Host", "")
        self.__class__.seen["path"] = self.path
        body = self._read_json()
        self.__class__.seen["body"] = body
        st = self.__class__.state
        if self.path == "/api/harness/enable":
            hid = body.get("id")
            if hid and hid not in st["enabled"]:
                st["enabled"].append(hid)
            return self._json(_okstratr_list_payload(enabled=list(st["enabled"])))
        if self.path == "/api/harness/disable":
            hid = body.get("id")
            st["enabled"] = [x for x in st["enabled"] if x != hid] or ["grok"]
            return self._json(_okstratr_list_payload(enabled=list(st["enabled"])))
        if self.path == "/api/harness/set":
            return self._json(_okstratr_list_payload(enabled=list(st["enabled"])))
        if self.path == "/api/harness/reload":
            return self._json(
                {
                    "ok": True,
                    "reloaded": True,
                    "config": _okstratr_list_payload(enabled=list(st["enabled"])),
                }
            )
        return self._json({"error": "not found"}, 404)


@pytest.fixture()
def stub_okstratr(monkeypatch):
    _StubOkstratr.state = {"enabled": ["grok"]}
    _StubOkstratr.seen = {}
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _StubOkstratr)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    monkeypatch.setenv("OKBAY_OKSTRATR_UPSTREAM", f"http://127.0.0.1:{port}")
    try:
        yield httpd, port
    finally:
        httpd.shutdown()


def test_call_harness_list_against_stub(stub_okstratr):
    view = okstratr_harness.list_harnesses()
    assert _StubOkstratr.seen["host"] == "okbay"
    assert _StubOkstratr.seen["path"] == "/api/harness"
    assert view["ssot"] == "okstratr"
    assert any(h["id"] == "grok" for h in view["harnesses"])


def test_call_harness_enable_posts_id(stub_okstratr):
    view = okstratr_harness.enable_harness("codex")
    assert _StubOkstratr.seen["path"] == "/api/harness/enable"
    assert _StubOkstratr.seen["body"]["id"] == "codex"
    assert "codex" in view["enabled"]


def test_call_harness_set_posts_key_value(stub_okstratr):
    okstratr_harness.set_harness_value("harness.grok.default_model", "grok-4")
    assert _StubOkstratr.seen["body"] == {
        "key": "harness.grok.default_model",
        "value": "grok-4",
    }


def test_call_harness_reload_unwraps_config(stub_okstratr):
    view = okstratr_harness.reload_harnesses()
    assert view["ssot"] == "okstratr"
    assert view["ok"] is True


def test_daemon_routes_thin_client(stub_okstratr, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws"))
    from okbay import paths

    paths.ensure_workspace(tmp_path / "ws")

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)

        conn.request("GET", "/api/okstratr/harness")
        res = conn.getresponse()
        data = json.loads(res.read().decode())
        assert res.status == 200
        assert data["ssot"] == "okstratr"
        assert data["ok"] is True
        assert data["host"] == "okbay"

        payload = json.dumps({"id": "claude"}).encode()
        conn.request(
            "POST",
            "/api/okstratr/harness/enable",
            body=payload,
            headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
        )
        res = conn.getresponse()
        data = json.loads(res.read().decode())
        assert res.status == 200
        assert "claude" in data["enabled"]

        payload = json.dumps({"id": "claude"}).encode()
        conn.request(
            "POST",
            "/api/okstratr/harness/disable",
            body=payload,
            headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
        )
        res = conn.getresponse()
        data = json.loads(res.read().decode())
        assert res.status == 200
        assert "claude" not in data["enabled"]

        payload = json.dumps({"key": "backend", "value": "direct"}).encode()
        conn.request(
            "POST",
            "/api/okstratr/harness/set",
            body=payload,
            headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
        )
        res = conn.getresponse()
        data = json.loads(res.read().decode())
        assert res.status == 200
        assert data["ssot"] == "okstratr"

        payload = b"{}"
        conn.request(
            "POST",
            "/api/okstratr/harness/reload",
            body=payload,
            headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
        )
        res = conn.getresponse()
        data = json.loads(res.read().decode())
        assert res.status == 200
        assert data["ssot"] == "okstratr"
        conn.close()
    finally:
        httpd.shutdown()


def test_daemon_route_502_when_upstream_down(monkeypatch, tmp_path):
    monkeypatch.setenv("OKBAY_OKSTRATR_UPSTREAM", "http://127.0.0.1:1")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws"))
    from okbay import paths

    paths.ensure_workspace(tmp_path / "ws")

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/api/okstratr/harness")
        res = conn.getresponse()
        data = json.loads(res.read().decode())
        conn.close()
        assert res.status == 502
        assert data["ok"] is False
        assert data["ssot"] == "okstratr"
    finally:
        httpd.shutdown()


def test_cli_harness_list(stub_okstratr, capsys):
    from okbay.cli import main

    code = main(["harness", "list"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ssot"] == "okstratr"
    assert any(h["id"] == "grok" for h in data["harnesses"])


def test_cli_harness_enable(stub_okstratr, capsys):
    from okbay.cli import main

    code = main(["harness", "enable", "codex"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert "codex" in data["enabled"]


def test_status_hint_includes_harness_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.delenv("OKBAY_OKSTRATR_UPSTREAM", raising=False)
    from okbay import paths, status

    paths.ensure_workspace(tmp_path / "ws")
    snap = status.compute(tmp_path / "ws")
    assert snap["harness_registry"]["ssot"] == "okstratr"
    assert snap["harness_registry"]["api"] == "/api/okstratr/harness"
    assert "okbay harness" in snap["harness_registry"]["cli"]
