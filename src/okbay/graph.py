"""Wiki graph JSON."""
from __future__ import annotations
import json
from . import paths
from .wiki import list_pages

def rebuild(ws=None):
    pages = list_pages(paths.wiki(ws))
    nodes = [{"id": p.stem, "title": p.title, "kind": p.kind} for p in pages]
    edges = []
    stems = {p.stem for p in pages}
    for p in pages:
        for link in p.links:
            if link in stems:
                edges.append({"source": p.stem, "target": link})
    g = {"pages": len(pages), "nodes": nodes, "edges": edges}
    path = paths.graph_json(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(g, indent=2), encoding="utf-8")
    return g

def load(ws=None):
    p = paths.graph_json(ws)
    if p.exists():
        return json.loads(p.read_text())
    return rebuild(ws)

def search_graph(g, q):
    q = (q or "").lower()
    return [n for n in g.get("nodes") or [] if q in json.dumps(n).lower()]
