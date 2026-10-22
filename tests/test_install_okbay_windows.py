"""contrib/install-okbay-windows.sh wires okbay-windows.lua into hyprland.lua once."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "contrib" / "install-okbay-windows.sh"


def _run(tmp_path: Path) -> str:
    env = {**os.environ, "XDG_CONFIG_HOME": str(tmp_path), "OKBAY_NO_RELOAD": "1"}
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=True).stdout


def test_installs_and_requires_once(tmp_path):
    hypr = tmp_path / "hypr"
    hypr.mkdir()
    main = hypr / "hyprland.lua"
    main.write_text('require("hypr.bindings")\n')
    _run(tmp_path)
    _run(tmp_path)
    assert (hypr / "okbay-windows.lua").read_text() == (ROOT / "contrib" / "okbay-windows.lua").read_text()
    assert main.read_text().count('require("hypr.okbay-windows")') == 1
    assert main.read_text().startswith('require("hypr.bindings")\n')


def test_skips_hyprlang_setups(tmp_path):
    (tmp_path / "hypr").mkdir()
    (tmp_path / "hypr" / "hyprland.conf").write_text("")
    out = _run(tmp_path)
    assert "skipping" in out
    assert not (tmp_path / "hypr" / "okbay-windows.lua").exists()


def test_setup_and_guest_apply_call_it():
    for name in ("setup.sh", "guest-apply-full-product.sh"):
        assert "install-okbay-windows.sh" in (ROOT / "contrib" / name).read_text(), name
