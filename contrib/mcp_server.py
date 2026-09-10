#!/usr/bin/env python3
"""Stdio MCP server for Okbay."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from okbay import desks, graph, ingest, locate, reviews, search, wiki
TOOLS = [
    {"name": "search_wiki", "description": "Search the Okbay wiki", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "read_wiki_page", "description": "Read a wiki page", "inputSchema": {"type": "object", "properties": {"stem": {"type": "string"}}, "required": ["stem"]}},
    {"name": "ingest", "description": "Ingest a file", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "propose_wiki_page", "description": "Stage a wiki page", "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}, "body": {"type": "string"}, "kind": {"type": "string"}}, "required": ["title", "body"]}},
    {"name": "list_reviews", "description": "Pending reviews", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "resolve_review", "description": "Accept or reject", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "action": {"type": "string"}}, "required": ["id", "action"]}},
    {"name": "desk_start", "description": "Seat a desk", "inputSchema": {"type": "object", "properties": {"kind": {"type": "string"}, "objective": {"type": "string"}}, "required": ["kind"]}},
]
def call(name, args):
    if name == "search_wiki": return search.search(args.get("query") or "")
    if name == "read_wiki_page":
        page = wiki.get_page(args.get("stem") or "")
        return {"ok": False, "error": "not found"} if not page else {"stem": page.stem, "title": page.title, "body": page.body, "kind": page.kind}
    if name == "ingest": return ingest.ingest_path(args.get("path") or "")
    if name == "propose_wiki_page": return reviews.propose(args.get("title") or "untitled", args.get("body") or "", kind=args.get("kind") or "note")
    if name == "list_reviews": return {"reviews": reviews.list_reviews()}
    if name == "resolve_review": return reviews.resolve(args.get("id"), args.get("action") or "reject")
    if name == "desk_start": return desks.start(args.get("kind") or "curate", args.get("objective") or "")
    return {"error": name}
def reply(msg_id, result=None, error=None):
    payload = {"jsonrpc": "2.0", "id": msg_id}
    payload["error" if error else "result"] = error or result
    sys.stdout.write(json.dumps(payload) + "\n"); sys.stdout.flush()
def main():
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try: req = json.loads(line)
        except json.JSONDecodeError: continue
        method, msg_id = req.get("method"), req.get("id")
        if method == "initialize":
            reply(msg_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "okbay", "version": "0.1.0"}})
        elif method == "tools/list":
            reply(msg_id, {"tools": TOOLS})
        elif method == "tools/call":
            params = req.get("params") or {}
            reply(msg_id, {"content": [{"type": "text", "text": json.dumps(call(params.get("name") or "", params.get("arguments") or {}), default=str)}]})
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
