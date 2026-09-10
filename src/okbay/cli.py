"""okbay command-line."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def _print(data, as_json=False):
    print(json.dumps(data, indent=2, default=str) if as_json or isinstance(data, (dict, list)) else data)
    return 0

def main(argv=None):
    p = argparse.ArgumentParser(prog="okbay")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup"); s.add_argument("--workspace")
    sub.add_parser("status")
    se = sub.add_parser("search"); se.add_argument("query"); se.add_argument("--json", action="store_true")
    ing = sub.add_parser("ingest"); ing.add_argument("path")
    pr = sub.add_parser("propose"); pr.add_argument("--title", required=True); pr.add_argument("--body", default=""); pr.add_argument("--kind", default="note")
    rv = sub.add_parser("reviews"); rv.add_argument("--json", action="store_true")
    rva = sub.add_parser("review"); rva.add_argument("action"); rva.add_argument("id")
    ds = sub.add_parser("desk"); dsub = ds.add_subparsers(dest="desk_cmd"); st = dsub.add_parser("start"); st.add_argument("kind"); st.add_argument("objective", nargs="?")
    sv = sub.add_parser("serve"); sv.add_argument("--host", default="127.0.0.1"); sv.add_argument("--port", type=int, default=8766)
    args = p.parse_args(argv)
    if args.cmd == "setup":
        from . import paths, status, graph
        ws = Path(args.workspace).expanduser() if args.workspace else paths.default_workspace()
        root = paths.ensure_workspace(ws)
        graph.rebuild(root)
        return _print(status.snapshot())
    if args.cmd == "status":
        from . import status
        return _print(status.snapshot())
    if args.cmd == "search":
        from . import search
        return _print(search.search(args.query), True)
    if args.cmd == "ingest":
        from . import ingest
        return _print(ingest.ingest_path(args.path))
    if args.cmd == "propose":
        from . import reviews
        return _print(reviews.propose(args.title, args.body, kind=args.kind))
    if args.cmd == "reviews":
        from . import reviews
        return _print(reviews.list_reviews())
    if args.cmd == "review":
        from . import reviews
        return _print(reviews.resolve(args.id, args.action))
    if args.cmd == "desk":
        from . import desks
        if args.desk_cmd == "start":
            return _print(desks.start(args.kind, args.objective or ""))
        return _print(desks.status() or {})
    if args.cmd == "serve":
        from . import server
        return server.serve(args.host, args.port)
    return 1
