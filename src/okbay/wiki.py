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
        # CE pages often use type:; prefer kind, then type, for Atlas palette fidelity.
        kind = str(front.get("kind") or front.get("type") or kind)
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

_STEM_INDEX: dict[str, Path] = {}
_STEM_INDEX_ROOT: Path | None = None
_STEM_INDEX_BUILT_AT: float = 0.0


def _wiki_mtime(directory: Path) -> float:
    try:
        return directory.stat().st_mtime
    except OSError:
        return 0.0


def _stem_index(directory: Path) -> dict[str, Path]:
    """Map file-stem → path. Built once per wiki root; avoids parsing 39k pages per modal open."""
    global _STEM_INDEX, _STEM_INDEX_ROOT, _STEM_INDEX_BUILT_AT
    mtime = _wiki_mtime(directory)
    if (
        _STEM_INDEX_ROOT == directory.resolve()
        and _STEM_INDEX
        and _STEM_INDEX_BUILT_AT >= mtime
    ):
        return _STEM_INDEX
    idx: dict[str, Path] = {}
    if directory.exists():
        for p in directory.rglob("*.md"):
            # Prefer first path for a stem; CE layout is wiki/<kind>/<stem>.md
            idx.setdefault(p.stem, p)
    _STEM_INDEX = idx
    try:
        _STEM_INDEX_ROOT = directory.resolve()
    except OSError:
        _STEM_INDEX_ROOT = directory
    _STEM_INDEX_BUILT_AT = mtime
    return idx



def get_page(stem: str, wiki_dir: Path | None = None) -> Page | None:
    from . import paths
    directory = wiki_dir or paths.wiki()
    if not stem:
        return None
    slug = slugify(stem)

    if not directory.exists():
        return None

    # 1) Flat wiki/<stem>.md
    direct = directory / f"{slug}.md"
    if direct.is_file():
        return parse_page(direct)

    # 2) Nested CE layout via stem index (one rglob to build, then O(1); no parse-all).
    idx = _stem_index(directory)
    hit = idx.get(slug) or idx.get(stem)
    if hit is not None and hit.is_file():
        return parse_page(hit)

    # 3) Last resort: single-name rglob (still no full parse).
    matches = list(directory.rglob(f"{slug}.md"))
    for p in matches:
        page = parse_page(p)
        if page is None:
            continue
        if page.stem == stem or page.stem == slug or page.title.lower() == stem.lower():
            return page
    if matches:
        return parse_page(matches[0])
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


# ── Slice 2: lazy atlas page payload (do not embed bodies in /api/atlas/data) ─

_WIKILINK_MD = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_MD_CODE = re.compile(r"`([^`]+)`")
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _html_escape(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def markdown_to_html(md: str) -> str:
    """Minimal markdown→HTML for the slim atlas modal (no external deps)."""
    if not md:
        return ""

    def format_inline(raw: str) -> str:
        tokens: list[str] = []

        def protect(pattern: re.Pattern, repl_fn, s: str) -> str:
            out: list[str] = []
            last = 0
            for m in pattern.finditer(s):
                out.append(s[last : m.start()])
                ph = f"\x00{len(tokens)}\x00"
                tokens.append(repl_fn(m))
                out.append(ph)
                last = m.end()
            out.append(s[last:])
            return "".join(out)

        s = protect(
            _WIKILINK_MD,
            lambda m: (
                f'<a class="wikilink" data-page="{_html_escape(m.group(1).strip())}" '
                f'href="#page={_html_escape(m.group(1).strip())}">'
                f"{_html_escape((m.group(2) or m.group(1)).strip())}</a>"
            ),
            raw,
        )
        s = protect(
            _MD_LINK,
            lambda m: f'<a href="{_html_escape(m.group(2))}">{_html_escape(m.group(1))}</a>',
            s,
        )
        s = protect(_MD_CODE, lambda m: f"<code>{_html_escape(m.group(1))}</code>", s)
        s = _html_escape(s)
        for i, tok in enumerate(tokens):
            s = s.replace(f"\x00{i}\x00", tok)
        s = _MD_BOLD.sub(r"<strong>\1</strong>", s)
        s = _MD_ITALIC.sub(r"<em>\1</em>", s)
        return s

    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    in_ul = False
    in_code = False
    code_buf: list[str] = []

    def flush_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                out.append("<pre><code>" + _html_escape("\n".join(code_buf)) + "</code></pre>")
                code_buf = []
                in_code = False
            else:
                flush_ul()
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue
        stripped = line.strip()
        if not stripped:
            flush_ul()
            continue
        if stripped.startswith("#"):
            flush_ul()
            level = len(stripped) - len(stripped.lstrip("#"))
            level = min(max(level, 1), 4)
            content = stripped[level:].strip()
            out.append(f"<h{level}>{format_inline(content)}</h{level}>")
            continue
        if stripped.startswith(("- ", "* ")):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{format_inline(stripped[2:].strip())}</li>")
            continue
        flush_ul()
        out.append(f"<p>{format_inline(stripped)}</p>")
    flush_ul()
    if in_code:
        out.append("<pre><code>" + _html_escape("\n".join(code_buf)) + "</code></pre>")
    return "\n".join(out)


def page_payload(stem: str, wiki_dir: Path | None = None) -> dict | None:
    """Lazy page doc for the atlas modal. Returns None if not found."""
    page = get_page(stem, wiki_dir=wiki_dir)
    if page is None:
        return None
    sources = list(page.sources or [])
    props: dict = {"sources": sources}
    for k, v in (page.front or {}).items():
        if k in ("stem", "title", "kind", "type", "sources", "extracted_from"):
            continue
        props[k] = v
    ntype = str(page.front.get("type") or page.kind or "note")
    return {
        "id": page.stem,
        "stem": page.stem,
        "title": page.title,
        "type": ntype,
        "kind": page.kind,
        "path": str(page.path),
        "properties": props,
        "sources": sources,
        "markdown": page.body,
        "body_html": markdown_to_html(page.body),
    }
