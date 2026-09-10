"""Propose → review → accept/reject. Agents never blind-write the wiki."""
from __future__ import annotations
import json
from pathlib import Path
from . import paths
from .wiki import slugify, write_page
from .store import connect

def _ledger_path() -> Path:
    p = paths.workspace() / ".okbay" / "reviews.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _write_ledger() -> None:
    try:
        rows = list_reviews("all")
    except Exception:
        return
    path = _ledger_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"reviews": rows}, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)

def propose(title: str, body: str, kind: str = "note", sources: list[str] | None = None, note: str = "", stems=None, reason: str = "", **kwargs) -> dict:
    stem = slugify(title)
    con = connect()
    with con:
        cur = con.execute(
            "INSERT INTO reviews(stem, title, body, kind, sources, reviewer_note, status) VALUES (?,?,?,?,?,?, 'pending')",
            (stem, title, body, kind, json.dumps(sources or stems or []), note or reason),
        )
        rid = cur.lastrowid
    con.close()
    draft = paths.reviews_dir() / f"{rid:04d}-{stem}.md"
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text(f"# DRAFT {title}\n\n{body}\n", encoding="utf-8")
    _write_ledger()
    return {"id": rid, "stem": stem, "status": "pending"}

def list_pending() -> list[dict]:
    con = connect()
    rows = con.execute("SELECT id, stem, title, kind, status, reviewer_note, created_at FROM reviews WHERE status = 'pending' ORDER BY id DESC").fetchall()
    con.close()
    return [dict(r) for r in rows]

def get(review_id: int) -> dict | None:
    con = connect()
    row = con.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    con.close()
    return dict(row) if row else None

def resolve(review_id, action: str = "", note: str = "") -> dict:
    if isinstance(review_id, str) and review_id.isdigit():
        review_id = int(review_id)
    elif isinstance(review_id, str) and not action:
        raise ValueError("resolve needs action")
    action = action or note
    action = action.lower().strip()
    if action not in {"accept", "reject", "edit"}:
        raise ValueError("action must be accept, reject, or edit")
    rec = get(review_id)
    if not rec:
        raise KeyError(f"review {review_id} not found")
    if rec["status"] != "pending":
        return rec
    if action == "accept":
        sources = json.loads(rec["sources"] or "[]")
        write_page(paths.wiki(), rec["stem"], rec["title"], rec["body"], kind=rec["kind"] or "note", sources=sources)
    con = connect()
    with con:
        con.execute("UPDATE reviews SET status = ?, reviewer_note = ? WHERE id = ?", (action + "ed" if action != "edit" else "accepted", note or rec["reviewer_note"], review_id))
    con.close()
    rec["status"] = "accepted" if action in {"accept", "edit"} else "rejected"
    _write_ledger()
    return rec

def pending_count() -> int:
    con = connect()
    n = con.execute("SELECT COUNT(*) FROM reviews WHERE status = 'pending'").fetchone()[0]
    con.close()
    return int(n)

def list_reviews(state: str = "pending") -> list[dict]:
    ledger = paths.workspace() / ".okbay" / "reviews.json"
    if ledger.is_file():
        try:
            raw = json.loads(ledger.read_text(encoding="utf-8"))
            rows = raw.get("reviews") if isinstance(raw, dict) else raw
            rows = list(rows or [])
            if state and state != "all":
                rows = [r for r in rows if (r or {}).get("status") == state]
            if rows:
                return rows
        except (OSError, json.JSONDecodeError):
            pass
    con = connect()
    if state and state != "all":
        rows = con.execute("SELECT id, stem, title, kind, status, reviewer_note, created_at FROM reviews WHERE status = ? ORDER BY id DESC", (state,)).fetchall()
    else:
        rows = con.execute("SELECT id, stem, title, kind, status, reviewer_note, created_at FROM reviews ORDER BY id DESC").fetchall()
    con.close()
    return [dict(r) for r in rows]
