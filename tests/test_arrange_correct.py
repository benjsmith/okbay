"""Unit tests for full-product arrange size/pos tolerance / Herdr correct heuristics."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARRANGE = ROOT / "contrib" / "okbay-arrange-full-product.py"


def _load():
    spec = importlib.util.spec_from_file_location("okbay_arrange_full_product", ARRANGE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def arrange():
    return _load()


def test_size_off_target_20pct(arrange):
    # half of 1920 = 960; 163 is way off; 800 within 20% of 960? |800-960|/960=0.166 < 0.20
    assert arrange.size_off_target(163, 500, 960, 524) is True
    assert arrange.size_off_target(960, 524, 960, 524) is False
    assert arrange.size_off_target(800, 524, 960, 524) is False  # ~16.7% < 20%
    assert arrange.size_off_target(700, 524, 960, 524) is True  # ~27% > 20%
    assert arrange.size_off_target(960, 100, 960, 524) is True  # height off


def test_pos_off_target_40px(arrange):
    assert arrange.pos_off_target(0, 24, 0, 24) is False
    assert arrange.pos_off_target(30, 24, 0, 24) is False  # within 40
    assert arrange.pos_off_target(41, 24, 0, 24) is True
    assert arrange.pos_off_target(0, 70, 0, 24) is True
    # Live Omarchy recenter failure: atlas at 1718,378 vs TL 0,24
    assert arrange.pos_off_target(1718, 378, 0, 24) is True
    assert arrange.pos_off_target(1715, 378, 1720, 732) is True  # okstratr vs BR


def test_herdr_narrow_needs_correct(arrange):
    target = (0, 532, 960, 524)
    meta = {"W": 1920, "H": 1080, "bar": 32}
    collapsed = {
        "size": [163, 524],
        "at": [0, 532],
        "floating": True,
        "fullscreen": 0,
        "address": "0x1",
    }
    needs, why = arrange.role_needs_correct("herdr", collapsed, target, meta)
    assert needs is True
    assert "163" in why or "herdr_narrow" in why or "size" in why


def test_atlas_ok_half(arrange):
    target = (0, 32, 960, 524)
    meta = {"W": 1920, "H": 1080}
    good = {
        "size": [960, 524],
        "at": [0, 32],
        "floating": True,
        "fullscreen": 0,
        "address": "0x2",
    }
    needs, why = arrange.role_needs_correct("atlas", good, target, meta)
    assert needs is False
    assert why.startswith("ok")


def test_atlas_pos_off_needs_correct(arrange):
    """Position off alone (size OK, floating) must trigger correct — WS13 smoke bug."""
    target = (0, 24, 1720, 708)
    meta = {"W": 3440, "H": 1440, "bar": 24}
    recentered = {
        "size": [1720, 708],
        "at": [1718, 378],
        "floating": True,
        "fullscreen": 0,
        "address": "0xA",
    }
    needs, why = arrange.role_needs_correct("atlas", recentered, target, meta)
    assert needs is True
    assert why.startswith("pos ")
    assert "1718" in why or "378" in why


def test_okstratr_pos_off_needs_correct(arrange):
    target = (1720, 732, 1720, 708)
    meta = {"W": 3440, "H": 1440, "bar": 24}
    wrong = {
        "size": [1720, 708],
        "at": [1715, 378],
        "floating": True,
        "fullscreen": 0,
        "address": "0xB",
    }
    needs, why = arrange.role_needs_correct("okstratr", wrong, target, meta)
    assert needs is True
    assert "pos" in why


def test_fs_full_cover_needs_correct(arrange):
    target = (0, 32, 960, 524)
    meta = {"W": 1920, "H": 1080}
    cover = {
        "size": [1920, 1080],
        "at": [0, 0],
        "floating": True,
        "fullscreen": 2,
        "address": "0x3",
    }
    needs, why = arrange.role_needs_correct("atlas", cover, target, meta)
    assert needs is True
    assert "fs" in why


def test_not_floating_needs_correct(arrange):
    target = (0, 532, 960, 524)
    tiled = {
        "size": [960, 524],
        "at": [0, 532],
        "floating": False,
        "fullscreen": 0,
        "address": "0x4",
    }
    needs, why = arrange.role_needs_correct("herdr", tiled, target, {"W": 1920, "H": 1080})
    assert needs is True
    assert "not_floating" in why


def test_not_floating_checked_before_pos(arrange):
    """Tiled tall panes (841x1392) must correct even if at happens to match."""
    target = (0, 24, 1720, 708)
    tiled = {
        "size": [841, 1392],
        "at": [0, 24],
        "floating": False,
        "fullscreen": 0,
        "address": "0x5",
    }
    needs, why = arrange.role_needs_correct("atlas", tiled, target, {"W": 3440, "H": 1440})
    assert needs is True
    assert "not_floating" in why


def test_layout_rects_half(arrange):
    layout, meta = arrange.layout_rects(
        {"width": 1920, "height": 1080, "x": 0, "y": 0, "reserved": [0, 32, 0, 0]}
    )
    assert meta["bar"] == 32
    assert layout["atlas"] == (0, 32, 960, 524)
    assert layout["herdr"][2] == 960  # half width ≥ 800
    assert layout["herdr"][2] >= 800


def test_layout_rects_ultrawide_bar24(arrange):
    layout, meta = arrange.layout_rects(
        {"width": 3440, "height": 1440, "x": 0, "y": 0, "reserved": [0, 24, 0, 0]}
    )
    assert meta["bar"] == 24
    assert layout["atlas"] == (0, 24, 1720, 708)
    assert layout["nautilus"] == (1720, 24, 1720, 708)
    assert layout["herdr"] == (0, 732, 1720, 708)
    assert layout["okstratr"] == (1720, 732, 1720, 708)


def test_role_score_prefers_floating_on_target(arrange):
    target_ws = "13"
    tiled = {
        "workspace": {"id": 13, "name": "13"},
        "floating": False,
        "fullscreen": 0,
        "size": [3440, 1400],
        "focusHistoryID": 1,
    }
    floating = {
        "workspace": {"id": 13, "name": "13"},
        "floating": True,
        "fullscreen": 0,
        "size": [1720, 708],
        "focusHistoryID": 2,
    }
    other_ws = {
        "workspace": {"id": 2, "name": "2"},
        "floating": True,
        "fullscreen": 0,
        "size": [1720, 708],
        "focusHistoryID": 0,
    }
    assert arrange.role_score(floating, target_ws) > arrange.role_score(tiled, target_ws)
    assert arrange.role_score(floating, target_ws) > arrange.role_score(other_ws, target_ws)
