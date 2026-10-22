"""contrib/okbay-windows.lua brings grok's sign-in window above the 2x2 layout."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LUA_FILE = ROOT / "contrib" / "okbay-windows.lua"
HARNESS = Path(__file__).resolve().parent / "okbay_windows_harness.lua"


def _lua() -> str:
    for name in ("lua", "lua5.4", "lua5.3", "luajit"):
        found = shutil.which(name)
        if found:
            return found
    pytest.skip("lua is not installed")


def _run() -> dict[str, str]:
    out = subprocess.run([_lua(), str(HARNESS), str(LUA_FILE)], capture_output=True, text=True, check=True)
    lines = {}
    for line in out.stdout.splitlines():
        key, _, rest = line.partition(": ")
        lines[key] = rest
    return lines


def test_new_signin_window_floats_centres_and_comes_forward():
    r = _run()
    assert r["fresh-open"] == ""
    assert r["fresh-title"] == (
        "float(address:0x1,toggle) resize(address:0x1,960x760) center(address:0x1) "
        "focus(address:0x1) bring_to_top(address:0x1)"
    )
    # Later title changes in the same window (the consent page) are left alone.
    assert r["fresh-again"] == ""


def test_existing_browser_window_is_only_focused():
    r = _run()
    assert r["old-title"] == "focus(address:0x2) bring_to_top(address:0x2)"


def test_other_pages_are_ignored():
    assert _run()["other"] == ""


def test_already_floating_window_is_not_toggled():
    assert _run()["floated-title"] == "focus(address:0x4) bring_to_top(address:0x4)"


def test_closed_window_state_is_forgotten():
    r = _run()
    assert r["reused"].startswith("float(address:0x1,toggle)")


def test_reloading_does_not_stack_handlers():
    assert _run()["handlers"] == "3 3"
