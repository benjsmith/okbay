"""SQLite FTS index over the wiki plus reviews and ingest ledger."""
from __future__ import annotations
import sqlite3
from pathlib import Path
from . import paths
from .wiki import list_pages

def db_path():
    return paths.state_dir() / "okbay.sqlite"

def connect() -> sqlite3.Connection:
    paths.state_dir().mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS pages (
            stem TEXT PRIMARY KEY, title TEXT, kind TEXT, path TEXT, body TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(stem, title, body);
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT, stem TEXT, title TEXT, body TEXT,
            kind TEXT, sources TEXT, reviewer_note TEXT, status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS ingest_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT, status TEXT, note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    return con

def reindex(ws: Path | None = None) -> int:
    root = ws or paths.workspace()
    pages = list_pages(paths.wiki(root))
    con = connect()
    with con:
        con.execute("DELETE FROM pages")
        try:
            con.execute("INSERT INTO pages_fts(pages_fts) VALUES('delete-all')")
        except sqlite3.OperationalError:
            try: con.execute("DELETE FROM pages_fts")
            except sqlite3.OperationalError: pass
        for p in pages:
            con.execute("INSERT INTO pages(stem, title, kind, path, body) VALUES (?,?,?,?,?)", (p.stem, p.title, p.kind, str(p.path), p.body))
            try:
                con.execute("INSERT INTO pages_fts(stem, title, body) VALUES (?,?,?)", (p.stem, p.title, p.body))
            except sqlite3.DatabaseError:
                pass
    n = len(pages)
    con.close()
    return n

def search(query: str, limit: int = 20) -> list[dict]:
    q = query.strip()
    try:
        con = connect()
    except sqlite3.DatabaseError:
        return []
    try:
        if not q:
            rows = con.execute("SELECT stem, title, kind, path FROM pages ORDER BY title LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
        try:
            rows = con.execute("SELECT stem, title, kind, path FROM pages_fts WHERE pages_fts MATCH ? LIMIT ?", (q, limit)).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.DatabaseError:
            rows = con.execute("SELECT stem, title, kind, path FROM pages WHERE title LIKE ? OR body LIKE ? LIMIT ?", (f"%{q}%", f"%{q}%", limit)).fetchall()
            return [dict(r) for r in rows]
    finally:
        try: con.close()
        except Exception: pass
