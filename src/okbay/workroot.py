"""Work-coverage root, opt-outs, and named workspaces.

Default experience: magically cover ~/Work (OKBAY_WORK_ROOT / coverage.toml).
The CE wiki/vault hub stays at ~/Work/okbay (OKBAY_WORKSPACE). Named workspaces
(e.g. biocure) are switched via `okbay workspace use`.
"""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from . import paths

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore


def config_dir() -> Path:
    p = paths.xdg_config() / "okbay"
    p.mkdir(parents=True, exist_ok=True)
    return p


def coverage_config_path() -> Path:
    return config_dir() / "coverage.toml"


def default_work_root() -> Path:
    override = os.environ.get("OKBAY_WORK_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return (paths.home() / "Work").resolve()


def _expand(raw: str | Path) -> Path:
    return Path(str(raw)).expanduser().resolve()


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file() or tomllib is None:
        return {}
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _quote_toml(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _dump_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    work_root = data.get("work_root")
    if work_root:
        lines.append(f"work_root = {_quote_toml(str(work_root))}")
    active = data.get("active_workspace")
    if active:
        lines.append(f"active_workspace = {_quote_toml(str(active))}")
    opt_out = data.get("opt_out") or []
    if opt_out:
        items = ", ".join(_quote_toml(str(x)) for x in opt_out)
        lines.append(f"opt_out = [{items}]")
    workspaces = data.get("workspaces") or {}
    if workspaces:
        if lines:
            lines.append("")
        lines.append("[workspaces]")
        for name, dest in sorted(workspaces.items()):
            lines.append(f"{name} = {_quote_toml(str(dest))}")
    lines.append("")
    return "\n".join(lines)


def load_coverage() -> dict[str, Any]:
    raw = _load_toml(coverage_config_path())
    workspaces = raw.get("workspaces") or {}
    if not isinstance(workspaces, dict):
        workspaces = {}
    opt_out = raw.get("opt_out") or []
    if isinstance(opt_out, str):
        opt_out = [opt_out]
    if not isinstance(opt_out, list):
        opt_out = []
    wr = raw.get("work_root")
    return {
        "work_root": str(_expand(wr)) if wr else str(default_work_root()),
        "opt_out": [str(x) for x in opt_out],
        "workspaces": {str(k): str(v) for k, v in workspaces.items()},
        "active_workspace": str(raw.get("active_workspace") or "") or None,
    }


def save_coverage(data: dict[str, Any]) -> Path:
    path = coverage_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "work_root": data.get("work_root") or str(default_work_root()),
        "opt_out": list(data.get("opt_out") or []),
        "workspaces": dict(data.get("workspaces") or {}),
    }
    if data.get("active_workspace"):
        payload["active_workspace"] = data["active_workspace"]
    path.write_text(_dump_toml(payload), encoding="utf-8")
    return path


def work_root() -> Path:
    cfg = load_coverage()
    env = os.environ.get("OKBAY_WORK_ROOT")
    if env:
        return _expand(env)
    return _expand(cfg["work_root"])


def is_opted_out(path: str | Path, cfg: dict[str, Any] | None = None) -> bool:
    """True if path matches an opt-out entry (exact prefix or glob)."""
    cfg = cfg or load_coverage()
    target = _expand(path)
    target_s = str(target)
    for entry in cfg.get("opt_out") or []:
        raw = str(entry).strip()
        if not raw:
            continue
        if any(ch in raw for ch in "*?[]"):
            # Glob against full path and against path relative to work_root.
            patterns = [raw, str(_expand(raw)) if not raw.startswith("*") else raw]
            try:
                rel = str(target.relative_to(work_root()))
            except ValueError:
                rel = target_s
            for pat in patterns:
                if fnmatch.fnmatch(target_s, pat) or fnmatch.fnmatch(rel, pat.lstrip("./")):
                    return True
                # Also allow ~/Work/foo style after expand without resolve of globs
                if fnmatch.fnmatch(target.name, pat):
                    return True
        else:
            base = _expand(raw)
            try:
                target.relative_to(base)
                return True
            except ValueError:
                if target_s == str(base):
                    return True
    return False


def opt_out(path: str | Path) -> dict[str, Any]:
    cfg = load_coverage()
    entry = str(Path(path).expanduser())
    outs = list(cfg.get("opt_out") or [])
    if entry not in outs and str(_expand(path)) not in {_expand(x) for x in outs if "*" not in x}:
        outs.append(entry)
    cfg["opt_out"] = outs
    save_coverage(cfg)
    return {"ok": True, "opt_out": outs, "path": entry}


def opt_in(path: str | Path) -> dict[str, Any]:
    cfg = load_coverage()
    entry = str(Path(path).expanduser())
    resolved = str(_expand(path))
    outs = []
    for x in cfg.get("opt_out") or []:
        xs = str(x)
        if xs == entry or xs == path or ( "*" not in xs and str(_expand(xs)) == resolved):
            continue
        outs.append(xs)
    cfg["opt_out"] = outs
    save_coverage(cfg)
    return {"ok": True, "opt_out": outs, "path": entry}


def list_workspaces() -> dict[str, Any]:
    cfg = load_coverage()
    named = dict(cfg.get("workspaces") or {})
    # Always surface the default hub.
    hub = str(paths.default_workspace())
    if "okbay" not in named:
        named = {"okbay": hub, **named}
    active = cfg.get("active_workspace")
    current = str(paths.workspace())
    return {
        "work_root": str(work_root()),
        "workspaces": named,
        "active": active,
        "current": current,
        "opt_out": list(cfg.get("opt_out") or []),
    }


def add_workspace(name: str, path: str | Path) -> dict[str, Any]:
    name = re.sub(r"[^a-z0-9_-]+", "-", name.strip().lower()).strip("-") or "ws"
    cfg = load_coverage()
    workspaces = dict(cfg.get("workspaces") or {})
    dest = str(Path(path).expanduser())
    workspaces[name] = dest
    cfg["workspaces"] = workspaces
    save_coverage(cfg)
    return {"ok": True, "name": name, "path": dest, "workspaces": workspaces}


def use_workspace(name: str) -> dict[str, Any]:
    cfg = load_coverage()
    workspaces = dict(cfg.get("workspaces") or {})
    hub = str(paths.default_workspace())
    if "okbay" not in workspaces:
        workspaces["okbay"] = hub
    if name not in workspaces:
        raise KeyError(f"unknown workspace: {name}")
    dest = _expand(workspaces[name])
    paths.ensure_workspace(dest)
    cfg["workspaces"] = workspaces
    cfg["active_workspace"] = name
    save_coverage(cfg)
    return {"ok": True, "name": name, "workspace": str(dest)}


def coverage_status() -> dict[str, Any]:
    cfg = load_coverage()
    return {
        "work_root": str(work_root()),
        "hub": str(paths.workspace()),
        "default_hub": str(paths.default_workspace()),
        "opt_out": list(cfg.get("opt_out") or []),
        "workspaces": dict(cfg.get("workspaces") or {}),
        "active_workspace": cfg.get("active_workspace"),
        "config": str(coverage_config_path()),
    }
