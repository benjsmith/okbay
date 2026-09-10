"""Search facade used by the HTTP server."""

from __future__ import annotations

from .wiki import search_pages


def search(query: str, limit: int = 20) -> dict:
    hits = search_pages(query or "", limit=limit)
    return {"hits": hits, "q": query or "", "count": len(hits)}
