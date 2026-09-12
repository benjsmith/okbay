"""Efficient coverage watcher: watchdog or mtime index + debounce."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from . import code_policy, ingest, paths, workroot

DEFAULT_DEBOUNCE_S = 2.5
MAX_FILES_PER_TICK = 40
HUGE_BYTES = 8_000_000
SKIP_NAMES = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "target", "dist", ".tox", ".pytest_cache",
}
TEXTISH = {
    ".md", ".txt", ".rst", ".csv", ".tsv", ".json", ".yaml", ".yml",
    ".toml", ".org", ".html", ".htm", ".xml", ".log", ".pdf", ".docx",
    ".odt", ".rtf", ".eml", ".markdown",
}


def debounce_ready(pending: dict[str, float], now: float, delay: float = DEFAULT_DEBOUNCE_S) -> list[str]:
    """Return keys whose last touch is at least `delay` seconds ago; remove them."""
    ready = [k for k, ts in pending.items() if now - ts >= delay]
    for k in ready:
        pending.pop(k, None)
    return ready


def should_skip_dir(name: str) -> bool:
    return name in SKIP_NAMES or (name.startswith(".") and name not in {".okbay"})


def is_watchable_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name.startswith("."):
        return False
    if code_policy.is_git_dir(path):
        return False
    try:
        if path.stat().st_size > HUGE_BYTES:
            return False
    except OSError:
        return False
    if path.suffix.lower() in TEXTISH or path.suffix == "":
        return True
    return len(path.suffix) <= 5


def mtime_db_path() -> Path:
    return paths.state_dir() / "watch_mtime.sqlite"


def _connect_mtime() -> sqlite3.Connection:
    con = sqlite3.connect(str(mtime_db_path()))
    con.execute(
        "CREATE TABLE IF NOT EXISTS mtimes (path TEXT PRIMARY KEY, mtime REAL, size INTEGER)"
    )
    return con


def iter_coverage_files(root: Path | None = None, cfg: dict | None = None) -> list[Path]:
    root = (root or workroot.work_root()).resolve()
    cfg = cfg or workroot.load_coverage()
    out: list[Path] = []
    if not root.is_dir():
        return out
    stack = [root]
    while stack:
        cur = stack.pop()
        if workroot.is_opted_out(cur, cfg):
            continue
        try:
            entries = list(cur.iterdir())
        except OSError:
            continue
        # Git repo that is not an okbay hub: note the repo root, do not descend.
        if (cur / ".git").exists() and cur != root and not code_policy.is_okbay_workspace(cur):
            out.append(cur)
            continue
        # Okbay hub checkout: only watch vault/ for doc drops (skip source tree).
        if (cur / ".git").exists() and code_policy.is_okbay_workspace(cur):
            vault = cur / "vault"
            if vault.is_dir() and not workroot.is_opted_out(vault, cfg):
                stack.append(vault)
            continue
        for ent in entries:
            if ent.is_dir():
                if should_skip_dir(ent.name) or workroot.is_opted_out(ent, cfg):
                    continue
                stack.append(ent)
            elif is_watchable_file(ent) and not workroot.is_opted_out(ent, cfg):
                out.append(ent)
    return out


def changed_since_index(files: list[Path], con: sqlite3.Connection | None = None) -> list[Path]:
    own = con is None
    con = con or _connect_mtime()
    changed: list[Path] = []
    try:
        for f in files:
            try:
                st = f.stat()
            except OSError:
                continue
            row = con.execute("SELECT mtime, size FROM mtimes WHERE path=?", (str(f),)).fetchone()
            if row is None or row[0] != st.st_mtime or row[1] != st.st_size:
                changed.append(f)
                con.execute(
                    "INSERT INTO mtimes(path, mtime, size) VALUES(?,?,?) "
                    "ON CONFLICT(path) DO UPDATE SET mtime=excluded.mtime, size=excluded.size",
                    (str(f), st.st_mtime, st.st_size),
                )
        con.commit()
    finally:
        if own:
            con.close()
    return changed


def handle_path(path: Path, confirm: bool = False, ws: Path | None = None) -> dict[str, Any]:
    """Apply policy for one changed path."""
    cfg = workroot.load_coverage()
    if workroot.is_opted_out(path, cfg):
        return {"ok": True, "skipped": True, "reason": "opt_out", "path": str(path)}
    if code_policy.is_git_dir(path):
        return {"ok": True, "skipped": True, "reason": "git_dir", "path": str(path)}
    if path.is_dir() and (path / ".git").exists() and not code_policy.is_okbay_workspace(path):
        return code_policy.note_repo_change(path, ws=ws)
    if code_policy.should_skip_code_ingest(path, ws=ws):
        return code_policy.note_repo_change(path, ws=ws)
    return ingest.ingest_path(path, ws=ws, confirm=confirm)


def tick(
    root: Path | None = None,
    confirm: bool = False,
    max_files: int = MAX_FILES_PER_TICK,
    ws: Path | None = None,
) -> dict[str, Any]:
    """One efficient pass: mtime-diff coverage files and process a batch."""
    cfg = workroot.load_coverage()
    files = iter_coverage_files(root, cfg)
    con = _connect_mtime()
    try:
        changed = changed_since_index(files, con)
    finally:
        con.close()
    batch = changed[:max_files]
    results = []
    for p in batch:
        try:
            results.append(handle_path(p, confirm=confirm, ws=ws))
        except Exception as exc:  # noqa: BLE001 — keep watcher alive
            results.append({"ok": False, "path": str(p), "error": str(exc)})
    return {
        "ok": True,
        "scanned": len(files),
        "changed": len(changed),
        "processed": len(batch),
        "results": results,
        "work_root": str(root or workroot.work_root()),
    }


def watch_once(**kwargs) -> dict[str, Any]:
    return tick(**kwargs)


def watch_serve(
    interval: float = 3.0,
    debounce: float = DEFAULT_DEBOUNCE_S,
    confirm: bool = False,
    root: Path | None = None,
    max_ticks: int | None = None,
) -> int:
    """Long-running loop. Prefer watchdog; fall back to periodic mtime ticks.

    `max_ticks` is for tests (stop after N iterations).
    """
    pending: dict[str, float] = {}
    use_watchdog = False
    observer = None
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event):  # noqa: N802
                if getattr(event, "is_directory", False):
                    return
                src = getattr(event, "src_path", None)
                if not src:
                    return
                pending[str(Path(src))] = time.time()

        root_path = Path(root or workroot.work_root())
        if root_path.is_dir():
            observer = Observer()
            observer.schedule(Handler(), str(root_path), recursive=True)
            observer.start()
            use_watchdog = True
    except Exception:
        use_watchdog = False
        observer = None

    ticks = 0
    try:
        while True:
            now = time.time()
            if use_watchdog and pending:
                ready = debounce_ready(pending, now, debounce)
                for raw in ready[:MAX_FILES_PER_TICK]:
                    handle_path(Path(raw), confirm=confirm)
            else:
                tick(root=root, confirm=confirm)
            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        if observer is not None:
            observer.stop()
            observer.join(timeout=2)
    return 0
