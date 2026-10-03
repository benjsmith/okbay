"""CE Atlas data bridge — build CuriosityDataSource-compatible CEData from okbay graph.

Slice 0: canvas payload only (stub body_html). See docs/CE-ATLAS-PARITY-AUDIT.md §3.3 / §7.
Endpoint: GET /api/atlas/data
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import graph as graph_mod
from . import paths, theme, wiki

# Mirror knowledge-atlas datasources/curiosity.ts TYPE_CANONICAL (singular forms).
_TYPE_CANONICAL = {
    "analysis": "analysis",
    "analyses": "analysis",
    "concept": "concept",
    "concepts": "concept",
    "entity": "entity",
    "entities": "entity",
    "evidence": "evidence",
    "fact": "fact",
    "facts": "fact",
    "figure": "figure",
    "figures": "figure",
    "table": "table",
    "tables": "table",
    "extracted-table": "table",
    "summary-table": "table",
    "source": "source",
    "sources": "source",
    "note": "note",
    "notes": "note",
    "todo": "todo-list",
    "todo-list": "todo-list",
    "project": "project",
    "projects": "project",
    "procedure": "procedure",
    "procedures": "procedure",
    "execution": "execution",
    "executions": "execution",
    "hub": "hub",
    "missing": "missing",
    "unclassified": "unclassified",
    "source-note": "source",
}

_PREFIX_TO_TYPE = {
    "con": "concept",
    "ent": "entity",
    "ana": "analysis",
    "src": "source",
    "evi": "evidence",
    "fact": "fact",
    "tbl": "table",
    "tab": "table",
    "fig": "figure",
    "note": "note",
    "todo": "todo-list",
    "proj": "project",
    "proc": "procedure",
    "exec": "execution",
}


def normalize_id(id_or_path: str) -> str:
    s = (id_or_path or "").strip()
    if s.endswith(".md"):
        return s[:-3]
    return s


def canonical_type(raw: str, title: str | None = None) -> str:
    key = (raw or "").strip().lower().replace(" ", "-")
    mapped = _TYPE_CANONICAL.get(key)
    if mapped and mapped != "unclassified":
        return mapped
    if title:
        # Title prefix like "[con] Foo" → concept (CE Switchbay backfill).
        t = title.strip()
        if t.startswith("[") and "]" in t:
            stem = t[1 : t.index("]")].strip().lower()
            back = _PREFIX_TO_TYPE.get(stem)
            if back:
                return back
    return mapped or (key if key in ("hub", "missing") else "unclassified")


def _is_file_id(nid: str) -> bool:
    return (nid or "").startswith("file:")


def _edge_endpoints(edge: dict) -> tuple[str, str]:
    src, tgt = edge.get("source"), edge.get("target")
    if isinstance(src, dict):
        src = src.get("id")
    if isinstance(tgt, dict):
        tgt = tgt.get("id")
    return normalize_id(str(src or "")), normalize_id(str(tgt or ""))


def _wiki_type_overrides(ws: Path | None) -> dict[str, str]:
    """Prefer CE frontmatter `type:` over stored kind when present."""
    overrides: dict[str, str] = {}
    try:
        for page in wiki.list_pages(paths.wiki(ws)):
            front = page.front or {}
            raw = front.get("type") or front.get("kind") or page.kind
            if raw:
                overrides[page.stem] = canonical_type(str(raw), page.title)
    except OSError:
        pass
    return overrides


def build_ce_data(
    graph: dict | None = None,
    ws: Path | None = None,
    palette: dict[str, str] | None = None,
    *,
    enrich_wiki_types: bool = False,
) -> dict[str, Any]:
    """Transform okbay `/graph` JSON into CEData for CuriosityDataSource.

    Uses node ``kind`` (canonicalised) by default. Pass ``enrich_wiki_types=True``
    to re-scan wiki frontmatter ``type:`` (costly on Biocure); prefer rebuilding
    the graph after the wiki ``type:``→kind parse instead.
    """
    root = ws or paths.workspace()
    g = graph if graph is not None else graph_mod.load(root)
    palette = palette if palette is not None else theme.type_palette()
    type_by_stem = _wiki_type_overrides(root) if enrich_wiki_types else {}

    raw_edges = g.get("edges") or []
    edges: list[dict[str, str]] = []
    degree: dict[str, int] = {}
    for e in raw_edges:
        src, tgt = _edge_endpoints(e)
        if not src or not tgt or _is_file_id(src) or _is_file_id(tgt):
            continue
        etype = str(e.get("type") or "wikilink")
        edges.append({"source": src, "target": tgt, "type": etype})
        degree[src] = degree.get(src, 0) + 1
        degree[tgt] = degree.get(tgt, 0) + 1

    nodes_out: list[dict[str, Any]] = []
    pages_out: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for n in g.get("nodes") or []:
        nid = normalize_id(str(n.get("id") or ""))
        if not nid or _is_file_id(nid) or nid in seen:
            continue
        seen.add(nid)
        title = str(n.get("title") or nid)
        raw_kind = str(n.get("kind") or n.get("type") or "note")
        ntype = type_by_stem.get(nid) or canonical_type(raw_kind, title)
        path = str(n.get("path") or "")
        sources = list(n.get("sources") or [])
        files = list(n.get("files") or [])
        deg = int(degree.get(nid, 0))
        nodes_out.append(
            {"id": nid, "path": path, "type": ntype, "title": title, "degree": deg}
        )
        pages_out[nid] = {
            "id": nid,
            "title": title,
            "type": ntype,
            "path": path,
            "properties": {"sources": sources, "files": files},
            "sources": sources,
            "files": files,
            "body_html": "",
        }

    # page_count: prefer integer from graph; else unique non-file nodes.
    page_count = g.get("pages")
    if not isinstance(page_count, int):
        page_count = len(nodes_out)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    graph_path = paths.graph_json(root)
    if graph_path.is_file():
        try:
            mtime = datetime.fromtimestamp(graph_path.stat().st_mtime, tz=timezone.utc)
            generated = mtime.strftime("%Y-%m-%dT%H:%M:%SZ")
        except OSError:
            pass

    return {
        "workspace": str(root),
        "generated_at": generated,
        "palette": dict(palette),
        "nodes": nodes_out,
        "edges": edges,
        "pages": pages_out,
        "page_count": page_count,
    }



def enrich_graph_kinds(ws: Path | None = None) -> dict[str, Any]:
    """One-shot: re-read wiki frontmatter ``type:`` into graph.json node kinds.

    Prefer this (or ``okbay graph rebuild``) over ``enrich_wiki_types=True`` on
    the hot ``/api/atlas/data`` path — Biocure ~40k pages is expensive per request.
    """
    root = ws or paths.workspace()
    g = graph_mod.load(root)
    overrides = _wiki_type_overrides(root)
    changed = 0
    for n in g.get("nodes") or []:
        nid = normalize_id(str(n.get("id") or ""))
        if not nid or nid not in overrides:
            continue
        new_kind = overrides[nid]
        if str(n.get("kind") or "") != new_kind:
            n["kind"] = new_kind
            changed += 1
    out = paths.graph_json(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(g, indent=2), encoding="utf-8")
    return {"ok": True, "changed": changed, "nodes": len(g.get("nodes") or []), "path": str(out)}


def load_ce(ws: Path | None = None) -> dict[str, Any]:
    return build_ce_data(ws=ws)
