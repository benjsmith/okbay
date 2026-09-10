"""Ingest raw files into the vault and mint a staging wiki page."""
from __future__ import annotations
import hashlib, shutil
from pathlib import Path
from . import paths
from .wiki import slugify, write_page

def ingest_path(src: str | Path, ws: Path | None = None, note: str = "") -> dict:
    root = ws or paths.workspace()
    src_path = Path(src).expanduser().resolve()
    if not src_path.exists():
        raise FileNotFoundError(src_path)
    vault = paths.vault(root)
    vault.mkdir(parents=True, exist_ok=True)
    dest = vault / src_path.name
    if dest.resolve() != src_path:
        if dest.exists():
            digest = hashlib.sha1(src_path.read_bytes()[:65536]).hexdigest()[:8]
            dest = vault / f"{src_path.stem}-{digest}{src_path.suffix}"
        shutil.copy2(src_path, dest)
    try:
        data = dest.read_bytes()
        text = "(binary)" if b"\x00" in data[:1024] else data.decode("utf-8", errors="replace")[:2000]
    except OSError as e:
        text = f"(unreadable: {e})"
    title = dest.stem.replace("_", " ").replace("-", " ")
    stem = slugify(title)
    page = write_page(paths.wiki(root), stem, title, f"Captured from `{dest.name}`.\n\n```\n{text}\n```\n", kind="source", sources=[dest.name])
    return {"ok": True, "vault": str(dest), "page": str(getattr(page, "path", page)), "stem": stem, "title": title, "note": note, "kind": "source"}
