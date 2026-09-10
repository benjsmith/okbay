"""XDG paths and workspace contract."""
from __future__ import annotations
import os
from pathlib import Path

def home() -> Path:
    return Path(os.environ.get("HOME") or Path.home())

def xdg_state() -> Path:
    raw = os.environ.get("XDG_STATE_HOME")
    return Path(raw) if raw else home() / ".local" / "state"

def state_dir() -> Path:
    p = xdg_state() / "okbay"
    p.mkdir(parents=True, exist_ok=True)
    return p

def status_path() -> Path:
    return state_dir() / "status.json"

def default_workspace() -> Path:
    override = os.environ.get("OKBAY_WORKSPACE")
    if override:
        return Path(override).expanduser()
    return home() / "Work" / "okbay"

def workspace() -> Path:
    marker = state_dir() / "workspace"
    if marker.exists():
        text = marker.read_text(encoding="utf-8").strip()
        if text:
            return Path(text)
    return default_workspace()

def set_workspace(path: Path) -> None:
    (state_dir() / "workspace").write_text(str(path), encoding="utf-8")

def vault(ws=None) -> Path:
    return (ws or workspace()) / "vault"

def wiki(ws=None) -> Path:
    return (ws or workspace()) / "wiki"

def curator(ws=None) -> Path:
    return (ws or workspace()) / ".curator"

def orchestrator(ws=None) -> Path:
    return (ws or workspace()) / ".orchestrator"

def reviews_dir(ws=None) -> Path:
    return (ws or workspace()) / ".okbay" / "reviews"

def graph_json(ws=None) -> Path:
    return curator(ws) / "graph.json"

def blackboard_path(ws=None) -> Path:
    return orchestrator(ws) / "blackboard.json"

def desks_path(ws=None) -> Path:
    return orchestrator(ws) / "desks.json"

def ensure_workspace(ws=None) -> Path:
    root = ws or workspace()
    for d in (root, vault(root), wiki(root), curator(root), orchestrator(root), reviews_dir(root), root / ".okbay"):
        d.mkdir(parents=True, exist_ok=True)
    set_workspace(root)
    return root

def ensure_layout(ws=None) -> Path:
    return ensure_workspace(ws)
