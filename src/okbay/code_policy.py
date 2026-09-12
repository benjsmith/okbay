"""Code-repo policy: never vault-copy source trees; beta/decision notes only."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from . import paths
from .wiki import slugify, write_page


def git_root(path: str | Path) -> Path | None:
    """Return nearest ancestor containing `.git`, else None."""
    cur = Path(path).expanduser().resolve()
    if cur.is_file():
        cur = cur.parent
    for candidate in (cur, *cur.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def is_okbay_workspace(path: str | Path) -> bool:
    """True if path is an okbay hub (vault + wiki layout)."""
    p = Path(path).expanduser().resolve()
    return (p / "vault").is_dir() and (p / "wiki").is_dir()


def is_under_workspace_vault(path: str | Path, ws: Path | None = None) -> bool:
    target = Path(path).expanduser().resolve()
    roots = []
    if ws is not None:
        roots.append(Path(ws).resolve())
    try:
        roots.append(paths.workspace().resolve())
    except Exception:
        pass
    for root in roots:
        vault = (root / "vault").resolve()
        try:
            target.relative_to(vault)
            return True
        except ValueError:
            continue
    return False


def is_under_git_repo(path: str | Path) -> bool:
    return git_root(path) is not None


def is_git_dir(path: str | Path) -> bool:
    p = Path(path)
    return p.name == ".git" or ".git" in p.parts


def should_skip_code_ingest(path: str | Path, ws: Path | None = None) -> bool:
    """True when path is inside a source tree that must not be vault-copied.

    Files already under the active workspace vault are allowed (drops).
    """
    if is_under_workspace_vault(path, ws=ws):
        return False
    root = git_root(path)
    if root is None:
        return False
    # Hub checkout: only treat non-vault paths as code.
    if is_okbay_workspace(root):
        return True
    return True


def note_repo_change(
    path: str | Path,
    ws: Path | None = None,
    tip: str = "",
) -> dict[str, Any]:
    """Record a lightweight decision/beta stub that a code repo changed.

    Never copies source into the vault.
    """
    root = ws or paths.workspace()
    paths.ensure_workspace(root)
    repo = git_root(path) or Path(path).expanduser().resolve()
    name = repo.name
    stem = slugify(f"repo-{name}-change")
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    tip_line = tip or "Review diffs in the repo; do not dump source into the vault."
    body = (
        f"Code repository `{repo}` changed at {ts}.\n\n"
        f"Trigger path: `{Path(path).expanduser()}`\n\n"
        f"**Policy:** source trees are not ingested. Capture decisions / beta notes only.\n\n"
        f"Tip: {tip_line}\n"
    )
    page = write_page(
        paths.wiki(root),
        stem,
        f"Repo change: {name}",
        body,
        kind="decision",
        sources=[],
        extra={"repo": str(repo), "policy": "code-no-ingest"},
    )
    bb = paths.blackboard_path(root)
    bb.parent.mkdir(parents=True, exist_ok=True)
    try:
        import json
        data = {}
        if bb.is_file():
            data = json.loads(bb.read_text(encoding="utf-8") or "{}")
        notes = list(data.get("code_repo_notes") or [])
        notes.append({"ts": time.time(), "repo": str(repo), "path": str(path), "page": stem})
        data["code_repo_notes"] = notes[-50:]
        bb.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except (OSError, ValueError):
        pass
    return {
        "ok": True,
        "skipped_ingest": True,
        "reason": "code_repo",
        "repo": str(repo),
        "page": str(getattr(page, "path", page)),
        "stem": stem,
        "kind": "decision",
    }
