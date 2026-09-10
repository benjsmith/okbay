from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .wiki import get_page
from . import paths


def locate(stem: str) -> dict[str, Any]:
    page = get_page(stem)
    if not page:
        return {"ok": False, "error": f"no page {stem}"}
    sources = page.front.get("extracted_from") or page.front.get("sources") or []
    resolved = []
    for src in sources if isinstance(sources, list) else [sources]:
        p = Path(str(src))
        if not p.is_absolute():
            p = paths.workspace() / p
        resolved.append(str(p))
    result = {
        "ok": True,
        "stem": page.stem,
        "title": page.title,
        "wiki": str(page.path),
        "sources": resolved,
    }
    target = resolved[0] if resolved else str(page.path)
    if shutil.which("hyprctl"):
        result["hypr"] = "available"
    if os.environ.get("OKBAY_REVEAL", "1") != "0":
        for cmd in (["xdg-open", str(Path(target).parent)],):
            if shutil.which(cmd[0]):
                try:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    result["revealed"] = cmd
                    break
                except OSError:
                    pass
    return result
