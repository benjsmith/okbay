"""Build a simple knowledge graph JSON from wiki pages."""
from __future__ import annotations
import json
from pathlib import Path
from . import paths
from .wiki import Page, list_pages

def build_graph(ws: Path | None = None) -> dict:
    root = ws or paths.workspace()
    pages = list_pages(paths.wiki(root))
    nodes, edges = [], []
    stems = {p.stem for p in pages}
    for p in pages:
        nodes.append({"id": p.stem, "title": p.title, "kind": p.kind, "path": str(p.path), "sources": p.sources, "files": _resolve_sources(root, p)})
        for dest in p.links:
            slug = dest.strip()
            edges.append({"source": p.stem, "target": slug, "type": "wikilink"})
            if slug not in stems:
                nodes.append({"id": slug, "title": slug, "kind": "missing", "path": "", "sources": [], "files": []})
                stems.add(slug)
        for src in p.sources:
            edges.append({"source": p.stem, "target": f"file:{src}", "type": "extracted_from"})
    graph = {"nodes": _dedupe_nodes(nodes), "edges": edges, "pages": len(pages)}
    out = paths.graph_json(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    return graph

def _dedupe_nodes(nodes):
    seen = {}
    for n in nodes:
        if n["id"] not in seen or n.get("kind") != "missing":
            seen[n["id"]] = n
    return list(seen.values())

def _resolve_sources(ws, page):
    files = []
    vault = paths.vault(ws)
    for src in page.sources:
        candidate = Path(src)
        if not candidate.is_absolute():
            candidate = vault / src
        if candidate.exists():
            files.append(str(candidate))
    return files

def search_graph(graph, query):
    q = query.strip().lower()
    if not q:
        return graph.get("nodes", [])[:40]
    hits = []
    for n in graph.get("nodes", []):
        blob = " ".join([n.get("id", ""), n.get("title", ""), n.get("kind", ""), " ".join(n.get("sources") or [])]).lower()
        if q in blob:
            hits.append(n)
    return hits

def rebuild(ws=None):
    data = build_graph(ws)
    data["links"] = len(data.get("edges") or [])
    return data

def load(ws=None):
    path = paths.graph_json(ws)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    data = build_graph(ws)
    data["links"] = len(data.get("edges") or [])
    return data
