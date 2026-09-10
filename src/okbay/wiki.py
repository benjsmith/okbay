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
        key = k.strip()
        val = v.strip().strip('"').strip("'")
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
    stem = path.stem
    title = stem.replace("-", " ").title()
    kind = "note"
    body = raw
    front: dict = {}
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
    pages = []
    for p in sorted(wiki_dir.rglob("*.md")):
        page = parse_page(p)
        if page:
            pages.append(page)
    return pages

def write_page(wiki_dir: Path | None = None, stem: str = "", title: str = "", body: str = "", kind: str = "note", sources: list[str] | None = None, extra: dict | None = None, **kwargs) -> Page:
    from . import paths
    if wiki_dir is None:
        wiki_dir = paths.wiki()
    title = title or kwargs.get("title") or stem
    stem = stem or kwargs.get("stem") or title
    extra = extra or kwargs.get("extra")
    if extra and not sources:
        sources = extra.get("extracted_from") or extra.get("sources")
    wiki_dir.mkdir(parents=True, exist_ok=True)
    stem = slugify(stem or title)
    path = wiki_dir / f"{stem}.md"
    lines = ["---", f"stem: {stem}", f"title: {title}", f"kind: {kind}"]
    if sources:
        lines.append(f"extracted_from: [{', '.join(sources)}]")
    if extra:
        for k, v in extra.items():
            if isinstance(v, list):
                lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
            else:
                lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    if not body.startswith("#"):
        lines.append(f"# {title}")
        lines.append("")
    lines.append(body.rstrip())
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    page = parse_page(path)
    if page is None:
        page = Page(stem=stem, path=path, title=title, kind=kind, body=body, front=extra or {}, links=[], sources=sources or [])
    return page

def get_page(stem: str, wiki_dir: Path | None = None) -> Page | None:
    from . import paths
    directory = wiki_dir or paths.wiki()
    if directory.exists():
        direct = directory / f"{slugify(stem)}.md"
        if direct.exists():
            return parse_page(direct)
        for page in list_pages(directory):
            if page.stem == stem or page.stem == slugify(stem) or page.title.lower() == stem.lower():
                return page
    return None

Page.meta = property(lambda self: self.front)

def search_pages(query: str, limit: int = 20) -> list[dict]:
    from .store import search as fts_search
    from .graph import load, search_graph
    q = (query or "").strip()
    hits = fts_search(q, limit=limit) if q else fts_search("", limit=limit)
    if hits:
        return hits
    graph_hits = search_graph(load(), q)
    if graph_hits:
        return graph_hits[:limit]
    out = []
    needle = q.lower()
    for page in list_pages():
        blob = f"{page.stem} {page.title} {page.kind} {page.body}".lower()
        if needle in blob:
            out.append({"stem": page.stem, "title": page.title, "kind": page.kind, "path": str(page.path)})
        if len(out) >= limit:
            break
    return out

def neighbors(stem: str) -> dict:
    from .graph import load
    g = load()
    incoming, outgoing = [], []
    for e in g.get("edges") or []:
        if e.get("source") == stem:
            outgoing.append(e)
        if e.get("target") == stem:
            incoming.append(e)
    return {"stem": stem, "outgoing": outgoing, "incoming": incoming}
