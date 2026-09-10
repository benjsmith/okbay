"""Markdown wiki pages with YAML-ish frontmatter and wikilinks."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
FRONT = re.compile(r"\A---\n(.*?)\n---\n?", re.S)

def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.strip().lower())
    return s.strip("-") or "page"

@dataclass
class Page:
    stem: str
    path: Path
    title: str
    kind: str = "note"
    body: str = ""
    front: dict = field(default_factory=dict)
    links: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    def text(self) -> str:
        return f"{self.title}\n{self.body}"

def _parse_front(raw: str) -> dict:
    meta: dict = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key, val = k.strip(), v.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            meta[key] = [p.strip().strip('"').strip("'") for p in inner.split(",") if p.strip()]
        else:
            meta[key] = val
    return meta

def parse_page(path: Path) -> Page | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    stem, title, kind, body, front = path.stem, path.stem.replace("-", " ").title(), "note", raw, {}
    m = FRONT.match(raw)
    if m:
        front = _parse_front(m.group(1))
        body = raw[m.end():]
        title = str(front.get("title") or title)
        kind = str(front.get("kind") or kind)
        stem = str(front.get("stem") or stem)
    links = [g.strip() for g in WIKILINK.findall(body)]
    sources = front.get("sources") or front.get("extracted_from") or []
    if isinstance(sources, str):
        sources = [sources]
    return Page(stem=stem, path=path, title=title, kind=kind, body=body, front=front, links=links, sources=list(sources))

def list_pages(wiki_dir: Path | None = None) -> list[Page]:
    from . import paths
    wiki_dir = wiki_dir or paths.wiki()
    if not wiki_dir.exists():
        return []
    return [p for p in (parse_page(x) for x in sorted(wiki_dir.rglob("*.md"))) if p]

def write_page(wiki_dir: Path | None = None, stem: str = "", title: str = "", body: str = "", kind: str = "note", sources: list[str] | None = None, extra: dict | None = None, **kwargs) -> Page:
    from . import paths
    wiki_dir = wiki_dir or paths.wiki()
    title = title or kwargs.get("title") or stem
    stem = slugify(stem or kwargs.get("stem") or title)
    wiki_dir.mkdir(parents=True, exist_ok=True)
    path = wiki_dir / f"{stem}.md"
    lines = ["---", f"stem: {stem}", f"title: {title}", f"kind: {kind}"]
    if sources:
        lines.append(f"extracted_from: [{', '.join(sources)}]")
    lines += ["---", "", f"# {title}", "", body.rstrip(), ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return parse_page(path) or Page(stem=stem, path=path, title=title, kind=kind, body=body)

def get_page(stem: str, wiki_dir: Path | None = None) -> Page | None:
    from . import paths
    directory = wiki_dir or paths.wiki()
    if directory.exists():
        direct = directory / f"{slugify(stem)}.md"
        if direct.exists():
            return parse_page(direct)
        for page in list_pages(directory):
            if page.stem == stem or page.stem == slugify(stem):
                return page
    return None

def search_pages(query: str, limit: int = 20) -> list[dict]:
    out, needle = [], (query or "").lower()
    for page in list_pages():
        blob = f"{page.stem} {page.title} {page.kind} {page.body}".lower()
        if not needle or needle in blob:
            out.append({"stem": page.stem, "title": page.title, "kind": page.kind, "path": str(page.path)})
        if len(out) >= limit:
            break
    return out
