"""Arrange policy tests for Omarchy 0.56 2x2 product."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "contrib" / "okbay-arrange-full-product.py"


def test_no_float_action_set_in_arrange():
    text = SRC.read_text()
    assert 'window.float' in text or "ensure_float" in text
    # Never emit Omarchy-hazardous float action=set
    assert 'action = "set"' not in text
    assert 'action = "toggle"' in text
    assert "Toggle only when tiled" in text or "NEVER float action=set" in text


def test_arrange_script_compiles():
    compile(SRC.read_text(), str(SRC), "exec")


def test_quadrant_layout_constants_present():
    text = SRC.read_text()
    assert '"atlas"' in text and '"nautilus"' in text
    assert '"herdr"' in text and '"okstratr"' in text


def _load():
    import importlib.util
    spec = importlib.util.spec_from_file_location("arrange", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_arrange_uses_opener_target_workspace(monkeypatch):
    mod = _load()
    monkeypatch.setenv("WS_TARGET", "2")
    monkeypatch.delenv("OKBAY_FULL_PRODUCT_WS", raising=False)
    assert mod.resolve_ws() == 2
    monkeypatch.setenv("OKBAY_FULL_PRODUCT_WS", "next-empty")
    assert mod.resolve_ws() == 2


def test_arrange_has_no_unreachable_default_workspace(monkeypatch):
    mod = _load()
    monkeypatch.delenv("WS_TARGET", raising=False)
    monkeypatch.delenv("OKBAY_FULL_PRODUCT_WS", raising=False)
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    assert mod.resolve_ws() == 1
    assert '"12"' not in SRC.read_text()
