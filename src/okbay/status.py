"""Write the status.json the QML surfaces poll. Keep this cheap."""
from __future__ import annotations
import json, time
from pathlib import Path
from . import paths

def _count_wiki_pages(wiki_dir: Path) -> int:
    if not wiki_dir.is_dir():
        return 0
    n = 0
    try:
        for p in wiki_dir.rglob("*.md"):
            if p.name.startswith("."):
                continue
            n += 1
    except OSError:
        return 0
    return n

def _graph_nodes(root: Path) -> int:
    p = paths.graph_json(root)
    if not p.is_file():
        return 0
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    return len(data.get("nodes") or [])

def _reviews_pending(root: Path) -> int:
    ledger = root / ".okbay" / "reviews.json"
    if ledger.is_file():
        try:
            rows = json.loads(ledger.read_text(encoding="utf-8"))
            if isinstance(rows, dict):
                rows = rows.get("reviews") or []
            return sum(1 for r in rows if (r or {}).get("status") == "pending")
        except (OSError, json.JSONDecodeError):
            pass
    try:
        from . import reviews
        return reviews.pending_count()
    except Exception:
        return 0

def _desk(root: Path):
    p = paths.desks_path(root)
    if not p.is_file():
        return None
    try:
        return (json.loads(p.read_text(encoding="utf-8")) or {}).get("active")
    except (OSError, json.JSONDecodeError):
        return None

def compute(ws: Path | None = None, state: str | None = None) -> dict:
    root = ws or paths.workspace()
    ready = (root / "wiki").exists()
    st = state or ("ready" if ready else "setup")
    from . import viewer_mutex
    vm = viewer_mutex.snapshot()
    # Cheap C1 core-skills health (no network spawn); full shape via /api/core-skills/status.
    try:
        from . import core_skills
        health = core_skills.status(root)
    except Exception:
        health = None
    try:
        from . import okstratr_harness
        harness = okstratr_harness.status_hint()
    except Exception:
        harness = {"ssot": "okstratr", "api": "/api/okstratr/harness"}
    return {
        "ts": time.time(),
        "state": st,
        "pages": _count_wiki_pages(paths.wiki(root)) if ready else 0,
        "nodes": _graph_nodes(root),
        "reviews_pending": _reviews_pending(root) if ready else 0,
        "desk": _desk(root),
        "atlas_url": "http://127.0.0.1:8766/atlas",
        "api_url": "http://127.0.0.1:8766",
        "workspace": str(root),
        "message": "" if ready else "Run okbay setup",
        "version": "0.1.0",
        "daemon": "python",
        "viewer_mode": vm["viewer_mode"],
        "html_ui_enabled": vm["html_ui_enabled"],
        "health": health,
        "harness_registry": harness,
    }

def write(ws: Path | None = None, state: str | None = None) -> dict:
    payload = compute(ws, state)
    dest = paths.status_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(dest)
    return payload

def rebuild(ws: Path | None = None) -> dict:
    from .graph import build_graph
    from .store import reindex
    root = ws or paths.workspace()
    reindex(root)
    build_graph(root)
    return write(root, state="ready")

def snapshot(ws=None, extra=None, state=None):
    if isinstance(ws, str) and ws in {"setup", "ready", "degraded", "curating", "missing"}:
        state, ws = ws, None
    payload = write(ws, state=state)
    if extra:
        payload.update(extra)
        dest = paths.status_path()
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(dest)
    return payload
