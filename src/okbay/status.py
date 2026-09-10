"""Cheap status.json snapshot."""
from __future__ import annotations
import json, time
from . import paths, desks, reviews

def snapshot(*args, **kwargs):
    ws = paths.ensure_workspace()
    wiki = paths.wiki(ws)
    pages = len(list(wiki.glob("*.md"))) if wiki.exists() else 0
    pending = len(reviews.list_reviews("pending"))
    desk = desks.status()
    snap = {
        "ts": time.time(),
        "state": "ready" if pages else "setup",
        "pages": pages,
        "reviews_pending": pending,
        "desk": desk,
        "atlas_url": "http://127.0.0.1:8766/atlas",
        "api_url": "http://127.0.0.1:8766",
        "workspace": str(ws),
        "daemon": "python",
    }
    paths.status_path().write_text(json.dumps(snap), encoding="utf-8")
    return snap
