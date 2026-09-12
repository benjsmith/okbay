"""Ingest raw files into the vault and mint a staging wiki page."""
from __future__ import annotations
import hashlib, shutil
from pathlib import Path
from . import code_policy, paths, privacy_gate, workroot
from .store import connect, reindex
from .wiki import slugify, write_page

def ingest_path(
    src: str | Path,
    ws: Path | None = None,
    note: str = "",
    confirm: bool = False,
    skip_privacy: bool = False,
) -> dict:
    root = ws or paths.workspace()
    src_path = Path(src).expanduser().resolve()
    if not src_path.exists():
        raise FileNotFoundError(src_path)

    cfg = workroot.load_coverage()
    if workroot.is_opted_out(src_path, cfg):
        return {
            "ok": False,
            "skipped": True,
            "reason": "opt_out",
            "path": str(src_path),
            "message": "Path is opted out in coverage.toml",
        }

    # Code repos: decision/beta note only (vault drops are exempt).
    if code_policy.should_skip_code_ingest(src_path, ws=root):
        return code_policy.note_repo_change(src_path, ws=root)

    if not skip_privacy:
        blocked = privacy_gate.gate_ingest(src_path, confirm=confirm)
        if blocked is not None:
            return blocked

    vault = paths.vault(root)
    vault.mkdir(parents=True, exist_ok=True)
    dest = vault / src_path.name
    if dest.resolve() != src_path:
        if dest.exists():
            digest = hashlib.sha1(src_path.read_bytes()[:65536]).hexdigest()[:8]
            dest = vault / f"{src_path.stem}-{digest}{src_path.suffix}"
        shutil.copy2(src_path, dest)
    text = _preview(dest)
    title = dest.stem.replace("_", " ").replace("-", " ")
    stem = slugify(title)
    page = write_page(
        paths.wiki(root),
        stem,
        title,
        f"Captured from `{dest.name}`.\n\n```\n{text}\n```\n",
        kind="source",
        sources=[dest.name],
    )
    con = connect()
    with con:
        con.execute(
            "INSERT INTO ingest_log(path, status, note) VALUES (?,?,?)",
            (str(dest), "staged", str(page)),
        )
    con.close()
    page_path = getattr(page, "path", page)
    reindex(root)
    return {
        "ok": True,
        "vault": str(dest),
        "page": str(page_path),
        "stem": stem,
        "title": title,
        "note": note,
        "kind": "source",
        "needs_confirm": False,
    }

def _preview(path: Path, limit: int = 2000) -> str:
    try:
        data = path.read_bytes()
    except OSError as e:
        return f"(unreadable: {e})"
    if b"\x00" in data[:1024]:
        return f"(binary {path.suffix or 'file'}, {len(data)} bytes)"
    text = data.decode("utf-8", errors="replace")
    return text[:limit]

def watch_new_vault_files(ws: Path | None = None) -> list[Path]:
    root = ws or paths.workspace()
    vault = paths.vault(root)
    wiki = paths.wiki(root)
    known = {p.stem for p in wiki.glob("*.md")}
    out = []
    if not vault.exists():
        return out
    for f in vault.iterdir():
        if f.name.startswith(".") or f.name == "README.md":
            continue
        if f.is_file() and slugify(f.stem) not in known:
            out.append(f)
    return out
