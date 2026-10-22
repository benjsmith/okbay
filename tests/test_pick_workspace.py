"""Super+Shift+K's "next-empty" picks the lowest empty workspace from 1 to 10."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENER = ROOT / "contrib" / "okbay-open-full-product.sh"


def _function_source() -> str:
    text = OPENER.read_text(encoding="utf-8")
    start = text.index("pick_workspace() {")
    end = text.index("\n}\n", start) + 3
    return text[start:end]


def _pick(tmp_path: Path, clients: list[dict], active: int = 1, env: dict | None = None) -> str:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    (tmp_path / "clients.json").write_text(json.dumps(clients))
    (tmp_path / "active.json").write_text(json.dumps({"id": active, "name": str(active)}))
    fake = bindir / "hyprctl"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        f'case "$1" in clients) cat "{tmp_path}/clients.json";; '
        f'activeworkspace) cat "{tmp_path}/active.json";; esac\n'
    )
    fake.chmod(0o755)
    run_env = {k: v for k, v in os.environ.items() if k != "OKBAY_FULL_PRODUCT_WS"}
    run_env["PATH"] = f"{bindir}:{run_env.get('PATH', '')}"
    run_env.update(env or {})
    script = _function_source() + "\npick_workspace\n"
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=run_env, check=True)
    return out.stdout.strip()


def _on(*ids: int) -> list[dict]:
    return [{"class": f"app{i}", "workspace": {"id": i, "name": str(i)}} for i in ids]


def test_picks_workspace_1_when_empty(tmp_path):
    assert _pick(tmp_path, _on(2, 3)) == "1"


def test_picks_lowest_gap(tmp_path):
    assert _pick(tmp_path, _on(1, 2, 4)) == "3"


def test_ignores_special_workspaces(tmp_path):
    assert _pick(tmp_path, _on(-98, 1)) == "2"


def test_stays_in_super_reachable_range(tmp_path):
    out = _pick(tmp_path, _on(*range(1, 11)), active=7)
    assert out == "7"
    assert _pick(tmp_path, _on(*range(1, 11), 11, 12), active=12) == "1"


def test_explicit_target_wins(tmp_path):
    assert _pick(tmp_path, _on(), env={"OKBAY_FULL_PRODUCT_WS": "5"}) == "5"
    assert _pick(tmp_path, _on(), env={"OKBAY_FULL_PRODUCT_WS": "special:okbay"}) == "special:okbay"


def test_no_hyprctl_falls_back_to_1():
    env = {"PATH": "/usr/bin:/bin"}
    script = _function_source() + "\ncommand() { [[ $2 == hyprctl ]] && return 1; builtin command \"$@\"; }\npick_workspace\n"
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, check=True)
    assert out.stdout.strip() == "1"
