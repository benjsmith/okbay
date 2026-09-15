"""Workspace-scoped Atlas host views (built-in + dynamic HTML decks)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import paths, reviews

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_BUILTIN = (
    {"id": "atlas", "title": "Atlas", "builtin": True, "kind": "atlas"},
    {"id": "viewer", "title": "Viewer", "builtin": True, "kind": "viewer"},
    {"id": "table", "title": "Table", "builtin": True, "kind": "table"},
    {"id": "library", "title": "Library", "builtin": True, "kind": "library"},
    {"id": "projects", "title": "Projects", "builtin": True, "kind": "projects"},
    {"id": "reviews", "title": "Reviews", "builtin": True, "kind": "reviews"},
)


def views_dir(ws: Path | None = None) -> Path:
    d = (ws or paths.workspace()) / ".okbay" / "views"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sanitize_id(view_id: str) -> str:
    view_id = (view_id or "").strip().lower()
    if not _ID_RE.match(view_id):
        raise ValueError("id must be [a-z0-9_-]{1,64} starting with alnum")
    if view_id in {b["id"] for b in _BUILTIN}:
        raise ValueError(f"id '{view_id}' is reserved for a built-in view")
    return view_id


def _meta_path(view_id: str, ws: Path | None = None) -> Path:
    return views_dir(ws) / f"{view_id}.json"


def _html_path(view_id: str, ws: Path | None = None) -> Path:
    return views_dir(ws) / f"{view_id}.html"


def _load_dynamic(ws: Path | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    root = views_dir(ws)
    for meta in sorted(root.glob("*.json")):
        try:
            raw = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        item = {
            "id": str(raw["id"]),
            "title": str(raw.get("title") or raw["id"]),
            "builtin": False,
            "kind": "dynamic",
            "workspace": str(raw.get("workspace") or ""),
            "ephemeral": bool(raw.get("ephemeral")),
            "url": raw.get("url") or f"/views/{raw['id']}",
            "has_html": _html_path(str(raw["id"]), ws).is_file(),
        }
        out.append(item)
    return out


def list_views(include_reviews_when_empty: bool = False) -> dict[str, Any]:
    """Built-in + registered dynamic views for the active workspace."""
    pending = reviews.pending_count()
    builtins: list[dict[str, Any]] = []
    for b in _BUILTIN:
        item = dict(b)
        if b["id"] == "reviews":
            item["pending"] = pending
            if pending <= 0 and not include_reviews_when_empty:
                continue
        builtins.append(item)
    dynamic = _load_dynamic()
    return {
        "ok": True,
        "workspace": str(paths.workspace()),
        "views": builtins + dynamic,
        "pending_reviews": pending,
    }


def get_view(view_id: str) -> dict[str, Any] | None:
    view_id = (view_id or "").strip().lower()
    for b in _BUILTIN:
        if b["id"] == view_id:
            item = dict(b)
            if view_id == "reviews":
                item["pending"] = reviews.pending_count()
            return item
    meta = _meta_path(view_id)
    if not meta.is_file():
        return None
    try:
        raw = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    raw = dict(raw)
    raw["builtin"] = False
    raw["kind"] = "dynamic"
    raw.setdefault("url", f"/views/{view_id}")
    raw["has_html"] = _html_path(view_id).is_file()
    return raw


def publish_view(
    view_id: str,
    title: str = "",
    html: str | None = None,
    url: str | None = None,
    workspace: str | None = None,
    ephemeral: bool = False,
) -> dict[str, Any]:
    """Register a dynamic sandboxed HTML (or external url) view."""
    vid = _sanitize_id(view_id)
    if not html and not url:
        raise ValueError("publish requires html or url")
    ws = paths.workspace()
    meta = {
        "id": vid,
        "title": (title or vid).strip() or vid,
        "workspace": workspace or str(ws),
        "ephemeral": bool(ephemeral),
        "url": url or f"/views/{vid}",
    }
    _meta_path(vid).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    if html is not None:
        # Store raw HTML; served under iframe sandbox (no parent script access).
        _html_path(vid).write_text(str(html), encoding="utf-8")
    elif _html_path(vid).is_file() and url:
        # External URL registration — drop stale local HTML if any.
        pass
    return {"ok": True, "view": get_view(vid)}


def delete_view(view_id: str) -> dict[str, Any]:
    vid = (view_id or "").strip().lower()
    if vid in {b["id"] for b in _BUILTIN}:
        raise ValueError("cannot delete built-in view")
    if not _ID_RE.match(vid):
        raise ValueError("invalid id")
    removed = False
    for p in (_meta_path(vid), _html_path(vid)):
        if p.is_file():
            p.unlink()
            removed = True
    if not removed:
        raise KeyError(f"view not found: {vid}")
    return {"ok": True, "id": vid, "deleted": True}


def view_html(view_id: str) -> str | None:
    vid = (view_id or "").strip().lower()
    if vid in {b["id"] for b in _BUILTIN}:
        return None
    path = _html_path(vid)
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def clear_ephemeral(ws: Path | None = None) -> int:
    """Remove ephemeral dynamic views (optional maintenance)."""
    n = 0
    for item in _load_dynamic(ws):
        if not item.get("ephemeral"):
            continue
        try:
            delete_view(item["id"])
            n += 1
        except (KeyError, ValueError):
            continue
    return n


def pages_table(limit: int = 5000) -> dict[str, Any]:
    """Lightweight page rows for Table / Library / Projects views."""
    from . import wiki

    rows = []
    for page in wiki.list_pages():
        ntype = str(page.front.get("type") or page.kind or "note")
        rows.append(
            {
                "id": page.stem,
                "stem": page.stem,
                "title": page.title,
                "kind": page.kind,
                "type": ntype,
                "path": str(page.path),
            }
        )
        if len(rows) >= limit:
            break
    return {"ok": True, "pages": rows, "count": len(rows)}


def accept_all_reviews() -> dict[str, Any]:
    """Dismissible Accept All — accept every pending review."""
    pending = reviews.list_reviews("pending")
    accepted = []
    errors = []
    for rec in pending:
        rid = rec.get("id")
        if rid is None:
            continue
        try:
            accepted.append(reviews.resolve(rid, "accept"))
        except Exception as exc:  # noqa: BLE001
            errors.append({"id": rid, "error": str(exc)})
    return {
        "ok": not errors,
        "accepted": len(accepted),
        "errors": errors,
        "pending_remaining": reviews.pending_count(),
    }
