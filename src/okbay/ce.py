from __future__ import annotations

import os
import shutil
from pathlib import Path


def ce_root() -> Path | None:
    env = os.environ.get("OKBAY_CE_ROOT") or os.environ.get("CURIOSITY_ENGINE_ROOT")
    candidates = []
    if env:
        candidates.append(Path(env).expanduser())
    home = Path.home()
    candidates += [
        home / ".claude" / "skills" / "curiosity-engine",
        home / ".agents" / "skills" / "curiosity-engine",
        home / "Dev" / "curiosity-engine",
    ]
    for c in candidates:
        if (c / "scripts").is_dir() or (c / "SKILL.md").is_file():
            return c
    return None


def available() -> bool:
    return ce_root() is not None or shutil.which("ce") is not None or shutil.which("curiosity-engine") is not None


def merge_root() -> Path | None:
    env = os.environ.get("OKBAY_CM_ROOT")
    candidates = []
    if env:
        candidates.append(Path(env).expanduser())
    home = Path.home()
    candidates += [
        home / ".claude" / "skills" / "curiosity-merge",
        home / ".agents" / "skills" / "curiosity-merge",
        home / "Dev" / "curiosity-merge",
    ]
    for c in candidates:
        if (c / "scripts" / "merge.py").is_file():
            return c
    return None
