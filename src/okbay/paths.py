"""XDG paths and workspace contract."""
from __future__ import annotations
import os
from pathlib import Path

def repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[2], here.parents[1], Path.cwd()):
        if (candidate / "manifest.json").is_file() or (candidate / "themes" / "switchbay").is_dir():
            return candidate
    return here.parents[2]

def home() -> Path:
    return Path(os.environ.get("HOME") or Path.home())

def xdg_state() -> Path:
    raw = os.environ.get("XDG_STATE_HOME")
    return Path(raw) if raw else home() / ".local" / "state"

def xdg_config() -> Path:
    raw = os.environ.get("XDG_CONFIG_HOME")
    return Path(raw) if raw else home() / ".config"

def xdg_runtime() -> Path:
    raw = os.environ.get("XDG_RUNTIME_DIR")
    return Path(raw) if raw else Path("/tmp") / f"okbay-{os.getuid()}"

def state_dir() -> Path:
    p = xdg_state() / "okbay"
    p.mkdir(parents=True, exist_ok=True)
    return p

def status_path() -> Path:
    return state_dir() / "status.json"

def db_path() -> Path:
    return state_dir() / "okbay.sqlite"

def log_path() -> Path:
    return state_dir() / "okbayd.log"

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
    state_dir().mkdir(parents=True, exist_ok=True)
    (state_dir() / "workspace").write_text(str(path), encoding="utf-8")

def vault(ws: Path | None = None) -> Path:
    return (ws or workspace()) / "vault"

def wiki(ws: Path | None = None) -> Path:
    return (ws or workspace()) / "wiki"

def curator(ws: Path | None = None) -> Path:
    return (ws or workspace()) / ".curator"

def orchestrator(ws: Path | None = None) -> Path:
    return (ws or workspace()) / ".orchestrator"

def reviews_dir(ws: Path | None = None) -> Path:
    return (ws or workspace()) / ".okbay" / "reviews"

def graph_json(ws: Path | None = None) -> Path:
    return curator(ws) / "graph.json"

def blackboard_path(ws: Path | None = None) -> Path:
    return orchestrator(ws) / "blackboard.json"

def desks_path(ws: Path | None = None) -> Path:
    return orchestrator(ws) / "desks.json"

def ensure_workspace(ws: Path | None = None) -> Path:
    root = ws or workspace()
    for d in (root, vault(root), wiki(root), curator(root), orchestrator(root), reviews_dir(root), root / ".okbay"):
        d.mkdir(parents=True, exist_ok=True)
    readme = vault(root) / "README.md"
    if not readme.exists():
        readme.write_text("# Vault\n\nDrop raw sources here. Do not organize them.\nOKBay extracts atomic wiki pages and graph edges from whatever lands.\n", encoding="utf-8")
    index = wiki(root) / "index.md"
    if not index.exists():
        index.write_text("---\nstem: index\ntitle: Home\nkind: hub\n---\n\n# Home\n\nThis is the OKBay wiki. Pages compound as you ingest and ask.\n", encoding="utf-8")
    set_workspace(root)
    return root

def ensure_layout(ws: Path | None = None) -> Path:
    return ensure_workspace(ws)

def config_dir() -> Path:
    p = xdg_config() / "okbay"
    p.mkdir(parents=True, exist_ok=True)
    return p

def coverage_config_path() -> Path:
    return config_dir() / "coverage.toml"

def work_root() -> Path:
    """Magical coverage root (~/Work). See okbay.workroot."""
    from . import workroot as wr
    return wr.work_root()
