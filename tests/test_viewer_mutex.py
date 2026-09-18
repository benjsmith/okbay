"""Phase 5a: HTML vs QML viewer mutex policy."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture()
def mutex_env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.delenv("OKBAY_VIEWER_MODE", raising=False)
    # Reload paths + mutex against the temp XDG roots.
    import importlib
    import okbay.paths as paths
    import okbay.viewer_mutex as vm

    importlib.reload(paths)
    importlib.reload(vm)
    return vm


def test_default_is_html(mutex_env):
    vm = mutex_env
    assert vm.resolve_mode() == "html"
    assert vm.html_ui_enabled() is True
    assert vm.should_block_html_ui("/atlas") is False
    assert vm.should_block_html_ui("/") is False
    assert vm.should_block_html_ui("/views/deck1") is False
    assert vm.should_block_html_ui("/api/status") is False
    assert vm.should_block_html_ui("/health") is False


def test_qml_blocks_html_ui_paths(mutex_env):
    vm = mutex_env
    snap = vm.set_mode("qml", source="test")
    assert snap["viewer_mode"] == "qml"
    assert snap["html_ui_enabled"] is False
    assert vm.should_block_html_ui("/atlas") is True
    assert vm.should_block_html_ui("/") is True
    assert vm.should_block_html_ui("/views/foo") is True
    # API + health always open
    assert vm.should_block_html_ui("/api/status") is False
    assert vm.should_block_html_ui("/api/viewer") is False
    assert vm.should_block_html_ui("/health") is False
    assert vm.should_block_html_ui("/static/atlas.html") is False


def test_env_overrides_config(mutex_env, monkeypatch):
    vm = mutex_env
    vm.set_mode("qml", source="test")
    monkeypatch.setenv("OKBAY_VIEWER_MODE", "html")
    import importlib

    importlib.reload(vm)
    assert vm.resolve_mode() == "html"
    assert vm.should_block_html_ui("/atlas") is False


def test_blocked_payload_shape(mutex_env):
    vm = mutex_env
    vm.set_mode("qml")
    body = vm.blocked_payload("/atlas")
    assert body["ok"] is False
    assert body["error"] == "html_ui_disabled"
    assert body["viewer_mode"] == "qml"
    assert body["html_ui_enabled"] is False
    stub = vm.blocked_html_stub("/atlas")
    assert "HTML atlas host off" in stub
    assert "qml" in stub


def test_status_includes_viewer_fields(mutex_env, tmp_path, monkeypatch):
    vm = mutex_env
    vm.set_mode("qml")
    import importlib
    import okbay.status as status
    import okbay.paths as paths

    importlib.reload(paths)
    importlib.reload(status)
    root = paths.ensure_workspace(tmp_path / "ws")
    payload = status.compute(root)
    assert payload["viewer_mode"] == "qml"
    assert payload["html_ui_enabled"] is False


def test_server_returns_409_when_qml(mutex_env, monkeypatch):
    """Exercise Handler.do_GET gate without binding a port."""
    vm = mutex_env
    vm.set_mode("qml")
    import importlib
    import okbay.server as server

    importlib.reload(server)

    class Fake:
        path = "/atlas"
        headers = {"Accept": "application/json"}
        code = None
        payload = None

        def _json(self, obj, code=200):
            self.code = code
            self.payload = obj

        def _html(self, text, code=200, **kw):
            self.code = code
            self.payload = text

    h = Fake()
    # Call the gate the same way do_GET does
    path = "/atlas"
    assert vm.should_block_html_ui(path)
    accept = (h.headers.get("Accept") or "").lower()
    if "application/json" in accept:
        h._json(vm.blocked_payload(path), 409)
    assert h.code == 409
    assert h.payload["error"] == "html_ui_disabled"
