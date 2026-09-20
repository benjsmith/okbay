"""Unit tests for full-product arrange size-tolerance / Herdr correct heuristics."""
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


def test_herdr_narrow_needs_correct(arrange):
    target = (0, 532, 960, 524)
    meta = {"W": 1920, "H": 1080, "bar": 32}
    collapsed = {
        "size": [163, 524],
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
        "floating": True,
        "fullscreen": 0,
        "address": "0x2",
    }
    needs, why = arrange.role_needs_correct("atlas", good, target, meta)
    assert needs is False
    assert why.startswith("ok")


def test_fs_full_cover_needs_correct(arrange):
    target = (0, 32, 960, 524)
    meta = {"W": 1920, "H": 1080}
    cover = {
        "size": [1920, 1080],
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
        "floating": False,
        "fullscreen": 0,
        "address": "0x4",
    }
    needs, why = arrange.role_needs_correct("herdr", tiled, target, {"W": 1920, "H": 1080})
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
