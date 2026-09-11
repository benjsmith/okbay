from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .wiki import get_page
from . import paths


def _which(name: str) -> str | None:
    return shutil.which(name)


def _spawn(cmd: list[str]) -> bool:
    """Start ``cmd`` detached; return True if spawn succeeded."""
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except OSError:
        return False


def _reveal_candidates(target: Path) -> list[list[str]]:
    """Ordered file-manager launch commands for Omarchy Nautilus → xdg-open.

    Omarchy ships Nautilus as the default file browser (``org.gnome.Nautilus``)
    and wraps launches with ``uwsm-app``. Prefer selecting an existing file
    (``nautilus --select``) so Reveal highlights it; otherwise open the parent
    directory. Fall back to ``xdg-open`` so non-Omarchy / headless hosts keep
    working when Nautilus is absent.
    """
    path = target
    parent = path.parent if path.parent.exists() else None
    is_file = path.is_file()
    is_dir = path.is_dir()
    open_dir = path if is_dir else parent
    if open_dir is None or not open_dir.exists():
        return []

    nautilus = _which("nautilus")
    uwsm = _which("uwsm-app")
    xdg = _which("xdg-open")
    cmds: list[list[str]] = []

    def add(cmd: list[str]) -> None:
        cmds.append(cmd)

    if nautilus:
        if is_file:
            select = [nautilus, "--select", str(path)]
            if uwsm:
                add([uwsm, "--", *select])
            add(select)
        # Directory (or missing file → parent): new window on that folder.
        win = [nautilus, "--new-window", str(open_dir)]
        if uwsm:
            add([uwsm, "--", *win])
        add(win)

    if xdg:
        add([xdg, str(open_dir)])

    return cmds


def reveal_path(target: str | Path) -> tuple[list[str] | None, str | None]:
    """Try native file browser then xdg-open. Returns (cmd, error)."""
    path = Path(target)
    candidates = _reveal_candidates(path)
    if not candidates:
        return None, "no file manager / path missing"
    last_err = "file manager launch failed"
    for cmd in candidates:
        if _spawn(cmd):
            return cmd, None
        last_err = f"failed to spawn {' '.join(cmd)}"
    return None, last_err


def locate(stem: str, *, reveal: bool | None = None) -> dict[str, Any]:
    """Resolve wiki + vault paths for a page stem.

    ``reveal`` defaults to env ``OKBAY_REVEAL`` (truthy unless ``0``). Pass
    ``reveal=False`` for resolve-only (atlas open / toast); ``True`` to open a
    file manager when available (Omarchy Nautilus preferred, else xdg-open).
    """
    page = get_page(stem)
    if not page:
        return {"ok": False, "error": f"no page {stem}"}
    sources = page.front.get("extracted_from") or page.front.get("sources") or page.sources or []
    if isinstance(sources, str):
        sources = [sources]
    vault = paths.vault()
    resolved: list[str] = []
    existing: list[str] = []
    for src in sources:
        p = Path(str(src))
        if not p.is_absolute():
            # Prefer vault/ (Biocure), then workspace-relative.
            cand = vault / src
            if not cand.exists():
                cand = paths.workspace() / src
            p = cand
        resolved.append(str(p))
        if p.exists():
            existing.append(str(p))
    files = existing or list(getattr(page, "files", []) or [])
    result: dict[str, Any] = {
        "ok": True,
        "stem": page.stem,
        "title": page.title,
        "wiki": str(page.path),
        "sources": resolved,
        "files": existing,
        "kind": page.kind,
    }
    # Prefer an on-disk vault/source file for highlight; else wiki page path.
    target = (existing[0] if existing else None) or (resolved[0] if resolved else str(page.path))
    result["target"] = target
    if _which("hyprctl"):
        result["hypr"] = "available"
    do_reveal = reveal
    if do_reveal is None:
        do_reveal = os.environ.get("OKBAY_REVEAL", "1") != "0"
    if do_reveal:
        cmd, err = reveal_path(target)
        if cmd:
            result["revealed"] = cmd
            # Friendly label for Atlas status toast (cmd may be absolute paths).
            joined = " ".join(cmd)
            if "nautilus" in joined:
                result["reveal_via"] = "nautilus"
            elif "xdg-open" in joined:
                result["reveal_via"] = "xdg-open"
            else:
                result["reveal_via"] = Path(cmd[0]).name
        else:
            result["reveal_error"] = err or "no file manager / path missing"
    else:
        result["revealed"] = None
    return result
