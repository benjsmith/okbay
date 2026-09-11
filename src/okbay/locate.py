from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .wiki import get_page
from . import paths


def locate(stem: str, *, reveal: bool | None = None) -> dict[str, Any]:
    """Resolve wiki + vault paths for a page stem.

    ``reveal`` defaults to env ``OKBAY_REVEAL`` (truthy unless ``0``). Pass
    ``reveal=False`` for resolve-only (atlas open / toast); ``True`` to open a
    file manager when available.
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
    target = (existing[0] if existing else None) or (resolved[0] if resolved else str(page.path))
    result["target"] = target
    if shutil.which("hyprctl"):
        result["hypr"] = "available"
    do_reveal = reveal
    if do_reveal is None:
        do_reveal = os.environ.get("OKBAY_REVEAL", "1") != "0"
    if do_reveal:
        parent = Path(target).parent if target else None
        if parent and parent.exists():
            for cmd in (["xdg-open", str(parent)],):
                if shutil.which(cmd[0]):
                    try:
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        result["revealed"] = cmd
                        break
                    except OSError:
                        pass
        if "revealed" not in result:
            result["reveal_error"] = "no file manager / path missing"
    else:
        result["revealed"] = None
    return result
