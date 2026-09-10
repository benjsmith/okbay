"""Optional sqlite FTS; body scan works without it."""
from __future__ import annotations
def connect():
    import sqlite3
    from . import paths
    p = paths.state_dir() / "okbay.sqlite"
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS ingest_log(path TEXT, status TEXT, note TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, stem TEXT, title TEXT, body TEXT, kind TEXT, sources TEXT, reviewer_note TEXT, status TEXT, created_at TEXT)")
    return con

def reindex(ws=None):
    return {"ok": True}

def search(query, limit=20):
    return []
