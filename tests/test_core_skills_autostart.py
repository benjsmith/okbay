"""C1 session auto-start: CE + okstratr helpers + viewer_mutex interaction."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture()
def autostart_env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.delenv("OKBAY_VIEWER_MODE", raising=False)
    monkeypatch.delenv("OKBAY_CE_EXTERNAL_VIEWER", raising=False)
    monkeypatch.delenv("OKBAY_OKSTRATR_UPSTREAM", raising=False)
    monkeypatch.delenv("OKBAY_CE_UPSTREAM", raising=False)

    import okbay.ce_supervisor as ce_sup
    import okbay.core_skills as core_skills
    import okbay.okstratr_supervisor as oks
    import okbay.paths as paths
    import okbay.viewer_mutex as vm

    importlib.reload(paths)
    importlib.reload(vm)
    importlib.reload(ce_sup)
    importlib.reload(oks)
    importlib.reload(core_skills)
    # Reset module latches / state
    core_skills.reset_for_tests()
    ce_sup._CE_STATE.update({"state": "stopped", "detail": ""})
    ce_sup._LOCAL_API_CLAIMED = False
    oks._STATE.update({"state": "stopped", "detail": ""})

    root = paths.ensure_workspace(tmp_path / "ws")
    (root / "wiki").mkdir(parents=True, exist_ok=True)
    (root / "wiki" / "hello.md").write_text("# Hello\n", encoding="utf-8")
    return {
        "paths": paths,
        "vm": vm,
        "ce": ce_sup,
        "oks": oks,
        "core": core_skills,
        "ws": root,
        "tmp": tmp_path,
    }


def test_okstratr_upstream_defaults(autostart_env):
    oks = autostart_env["oks"]
    assert oks.upstream_base() == "http://127.0.0.1:8767"
    assert oks.upstream_port() == 8767
    assert oks.health_url().endswith("/health")


def test_okstratr_upstream_env_override(autostart_env, monkeypatch):
    oks = autostart_env["oks"]
    monkeypatch.setenv("OKBAY_OKSTRATR_UPSTREAM", "http://127.0.0.1:9876")
    assert oks.upstream_base() == "http://127.0.0.1:9876"
    assert oks.upstream_port() == 9876


def test_okstratr_resolve_argv(autostart_env, monkeypatch, tmp_path):
    oks = autostart_env["oks"]
    fake = tmp_path / "okstratr-bin"
    fake.write_text("#!/bin/sh\n", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("OKBAY_OKSTRATR_BIN", str(fake))
    assert oks.resolve_okstratr_argv() == [str(fake)]
    monkeypatch.delenv("OKBAY_OKSTRATR_BIN")
    monkeypatch.setattr(oks.shutil, "which", lambda _n: None)
    assert oks.resolve_okstratr_argv()[-2:] == ["-m", "okstratr"]


def test_okstratr_contract_slice_shape(autostart_env, monkeypatch):
    oks = autostart_env["oks"]
    monkeypatch.setattr(oks, "is_healthy", lambda **_: False)
    monkeypatch.setattr(oks, "_read_pid", lambda: None)
    slice_ = oks.contract_slice()
    assert set(slice_) == {"state", "url", "detail"}
    assert slice_["state"] in {"starting", "healthy", "unhealthy", "stopped"}


def test_core_skills_status_shape(autostart_env, monkeypatch):
    env = autostart_env
    monkeypatch.setattr(
        env["ce"],
        "contract_slice",
        lambda _ws=None: {
            "state": "healthy",
            "url": "http://127.0.0.1:8766",
            "detail": "apis",
            "html_viewer_allowed": True,
            "viewer_mode": "html",
        },
    )
    monkeypatch.setattr(
        env["oks"],
        "contract_slice",
        lambda: {
            "state": "starting",
            "url": "http://127.0.0.1:8767",
            "detail": "spawning",
        },
    )
    monkeypatch.setattr(
        env["ce"],
        "wiki_build_slice",
        lambda: {"state": "idle", "pages": 1, "detail": ""},
    )
    out = env["core"].status(env["ws"])
    assert set(out) == {"ce", "okstratr", "wiki_build"}
    assert out["ce"]["state"] == "healthy"
    assert out["okstratr"]["state"] == "starting"
    assert out["wiki_build"]["state"] == "idle"


def test_ce_start_html_allows_atlas_host(autostart_env):
    env = autostart_env
    env["vm"].set_mode("html", source="test")
    out = env["ce"].start(env["ws"])
    assert out["ok"] is True
    assert out["html_viewer_allowed"] is True
    assert out["html_atlas_host"] is True
    assert out["apis"] is True
    assert env["ce"].html_viewer_allowed() is True
    slice_ = env["ce"].contract_slice(env["ws"])
    assert slice_["state"] == "healthy"
    assert slice_["html_viewer_allowed"] is True


def test_ce_start_qml_blocks_html_atlas_still_apis(autostart_env):
    """Mutex: QML on ⇒ no HTML atlas host; CE APIs still claimed healthy."""
    env = autostart_env
    env["vm"].set_mode("qml", source="test")
    out = env["ce"].start(env["ws"])
    assert out["ok"] is True
    assert out["html_viewer_allowed"] is False
    assert out["html_atlas_host"] is False
    assert out["apis"] is True
    assert out["external_viewer"].get("skipped") is True
    assert out["external_viewer"].get("reason") == "qml_mutex"
    # Mutex still blocks HTML UI paths
    assert env["vm"].should_block_html_ui("/atlas") is True
    assert env["vm"].should_block_html_ui("/api/graph") is False
    slice_ = env["ce"].contract_slice(env["ws"])
    assert slice_["state"] == "healthy"
    assert slice_["viewer_mode"] == "qml"
    assert "HTML atlas host off" in slice_["detail"] or "qml" in slice_["detail"].lower()


def test_external_viewer_spawn_refused_when_qml(autostart_env, monkeypatch):
    env = autostart_env
    env["vm"].set_mode("qml", source="test")
    monkeypatch.setenv("OKBAY_CE_EXTERNAL_VIEWER", "1")
    # Even with external flag, mutex refuses spawn.
    out = env["ce"]._spawn_external_viewer(env["ws"])
    assert out.get("skipped") is True
    assert out.get("error") == "html_ui_disabled"


def test_ensure_started_invokes_ce_and_okstratr(autostart_env, monkeypatch):
    env = autostart_env
    calls = {"ce": 0, "oks": 0}

    def fake_ce_start(ws):
        calls["ce"] += 1
        return {"ok": True, "html_viewer_allowed": True, "apis": True}

    def fake_oks_start(ws=None):
        calls["oks"] += 1
        return {"ok": True, "healthy": True, "url": "http://127.0.0.1:8767"}

    monkeypatch.setattr(env["ce"], "start", fake_ce_start)
    monkeypatch.setattr(env["oks"], "start", fake_oks_start)
    # Avoid background poller sleeping forever in tests
    monkeypatch.setattr(
        env["oks"],
        "poll_forever",
        lambda *a, **k: None,
    )

    out = env["core"].ensure_started(env["ws"], keep_alive=False, wait_okstratr=True)
    assert out["ok"] is True
    assert calls["ce"] == 1
    assert calls["oks"] == 1
    assert "status" in out
    assert set(out["status"]) == {"ce", "okstratr", "wiki_build"}


def test_status_snapshot_includes_health(autostart_env, monkeypatch):
    env = autostart_env
    import okbay.status as status

    importlib.reload(status)
    monkeypatch.setattr(
        env["core"],
        "status",
        lambda _ws=None: {
            "ce": {"state": "healthy", "url": "http://127.0.0.1:8766", "detail": "x"},
            "okstratr": {"state": "stopped", "url": "http://127.0.0.1:8767", "detail": ""},
            "wiki_build": {"state": "idle", "pages": None, "detail": ""},
        },
    )
    # Patch where status.compute imports it
    import okbay.core_skills as cs

    monkeypatch.setattr(
        cs,
        "status",
        lambda _ws=None: {
            "ce": {"state": "healthy", "url": "http://127.0.0.1:8766", "detail": "x"},
            "okstratr": {"state": "stopped", "url": "http://127.0.0.1:8767", "detail": ""},
            "wiki_build": {"state": "idle", "pages": None, "detail": ""},
        },
    )
    payload = status.compute(env["ws"])
    assert "health" in payload
    assert payload["health"]["ce"]["state"] == "healthy"
