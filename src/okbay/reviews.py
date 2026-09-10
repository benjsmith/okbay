"""Propose → review → accept/reject."""
from __future__ import annotations
import json, time
from pathlib import Path
from . import paths
from .wiki import slugify, write_page

def _ledger() -> Path:
    p = paths.workspace() / ".okbay" / "reviews.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _load():
    p = _ledger()
    if p.exists():
        try: return json.loads(p.read_text())
        except json.JSONDecodeError: pass
    return {"reviews": [], "next_id": 1}

def _save(data):
    _ledger().write_text(json.dumps(data, indent=2), encoding="utf-8")

def propose(title, body, kind="note", **kwargs):
    data = _load()
    rid = data.get("next_id", 1)
    rec = {"id": rid, "stem": slugify(title), "title": title, "body": body, "kind": kind, "status": "pending"}
    data["reviews"].append(rec)
    data["next_id"] = rid + 1
    _save(data)
    return rec

def list_reviews(state="pending"):
    rows = _load()["reviews"]
    if state and state != "all":
        rows = [r for r in rows if r.get("status") == state]
    return rows

def resolve(review_id, action="accept", note=""):
    data = _load()
    for rec in data["reviews"]:
        if str(rec["id"]) == str(review_id):
            rec["status"] = "accepted" if action == "accept" else "rejected"
            if action == "accept":
                write_page(None, rec["stem"], rec["title"], rec["body"], kind=rec.get("kind") or "note")
            _save(data)
            return rec
    raise KeyError(review_id)
