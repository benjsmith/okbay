"""okstratr.host_notify → Herdr stub I/O (contract C2)."""
from __future__ import annotations

import io
import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from okbay import host_notify, paths, server


def _env(**overrides):
    base = {
        "type": "okstratr.host_notify",
        "v": 1,
        "kind": "schedule.start",
        "schedule_id": "sched-1",
        "desk": "auto",
        "title": "Morning digest",
        "body": "Running hedge-fund desk.",
        "progress": {"pct": None, "phase": "start", "detail": ""},
        "ts": "2026-09-19T08:00:00Z",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def state_env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.delenv("OKBAY_HERDR_NOTIFY_LOG", raising=False)
    paths.ensure_workspace(tmp_path / "ws")
    return tmp_path


def test_validate_ok(state_env):
    env = host_notify.validate_envelope(_env())
    assert env["type"] == "okstratr.host_notify"
    assert env["kind"] == "schedule.start"
    assert env["title"] == "Morning digest"


def test_validate_rejects_wrong_type(state_env):
    with pytest.raises(host_notify.HostNotifyError, match="type"):
        host_notify.validate_envelope(_env(type="other"))


def test_validate_rejects_bad_kind(state_env):
    with pytest.raises(host_notify.HostNotifyError, match="kind"):
        host_notify.validate_envelope(_env(kind="nope"))


def test_validate_requires_title(state_env):
    with pytest.raises(host_notify.HostNotifyError, match="title"):
        host_notify.validate_envelope(_env(title=""))


def test_format_includes_title_meta_body(state_env):
    text = host_notify.format_herdr_line(_env())
    assert "Morning digest" in text
    assert "desk=auto" in text
    assert "id=sched-1" in text
    assert "Running hedge-fund desk." in text


def test_format_progress(state_env):
    text = host_notify.format_herdr_line(
        _env(
            kind="schedule.progress",
            progress={"pct": 40, "phase": "fetch", "detail": "n=3"},
        )
    )
    assert "40%" in text
    assert "fetch" in text
    assert "Schedule progress" in text


def test_receive_writes_jsonl_and_stderr(state_env, tmp_path):
    buf = io.StringIO()
    log = tmp_path / "herdr-notify.jsonl"
    result = host_notify.receive(_env(), log_path=log, stderr=buf)
    assert result["ok"] is True
    assert result["sink"] == "herdr"
    assert "Morning digest" in result["text"]
    assert log.is_file()
    line = json.loads(log.read_text(encoding="utf-8").strip())
    assert line["sink"] == "herdr"
    assert line["title"] == "Morning digest"
    assert line["envelope"]["kind"] == "schedule.start"
    err = buf.getvalue()
    assert err.startswith("herdr:")
    assert "Morning digest" in err


def test_receive_default_log_under_xdg_state(state_env):
    buf = io.StringIO()
    result = host_notify.receive(_env(), stderr=buf)
    assert result["ok"] is True
    log = Path(result["log"])
    assert log.name == "herdr-notify.jsonl"
    assert "okbay" in str(log)
    assert log.is_file()


def test_receive_invalid_returns_error(state_env):
    result = host_notify.receive({"type": "nope"}, write_log=False, print_stderr=False)
    assert result["ok"] is False
    assert "type" in result["error"]


def test_receive_json_text(state_env, tmp_path):
    buf = io.StringIO()
    log = tmp_path / "n.jsonl"
    raw = json.dumps(_env(kind="desk.done", title="Desk finished"))
    result = host_notify.receive_json_text(raw, log_path=log, stderr=buf)
    assert result["ok"] is True
    assert "Desk finished" in result["text"]


def test_cli_host_notify(state_env, tmp_path, monkeypatch, capsys):
    from okbay.cli import main

    monkeypatch.setenv("OKBAY_HERDR_NOTIFY_LOG", str(tmp_path / "cli.jsonl"))
    code = main(["host-notify", json.dumps(_env())])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["ok"] is True
    assert data["sink"] == "herdr"


def test_http_host_notify_endpoint(state_env, tmp_path, monkeypatch):
    monkeypatch.setenv("OKBAY_HERDR_NOTIFY_LOG", str(tmp_path / "http.jsonl"))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        payload = json.dumps(_env()).encode()
        conn.request(
            "POST",
            "/api/okstratr/host-notify",
            body=payload,
            headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
        )
        res = conn.getresponse()
        body = json.loads(res.read().decode())
        conn.close()
        assert res.status == 200
        assert body["ok"] is True
        assert body["sink"] == "herdr"
        assert "Morning digest" in body["text"]
        assert (tmp_path / "http.jsonl").is_file()
    finally:
        httpd.shutdown()


def test_http_rejects_bad_envelope(state_env, tmp_path, monkeypatch):
    monkeypatch.setenv("OKBAY_HERDR_NOTIFY_LOG", str(tmp_path / "bad.jsonl"))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        payload = json.dumps({"type": "wrong"}).encode()
        conn.request(
            "POST",
            "/api/okstratr/host-notify",
            body=payload,
            headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
        )
        res = conn.getresponse()
        body = json.loads(res.read().decode())
        conn.close()
        assert res.status == 400
        assert body["ok"] is False
    finally:
        httpd.shutdown()
