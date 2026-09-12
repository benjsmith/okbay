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
    ing = sub.add_parser("ingest")
    ing.add_argument("path")
    ing.add_argument("--confirm", action="store_true", help="Confirm ingest despite privacy/financial findings")
    pr = sub.add_parser("propose"); pr.add_argument("--title", required=True); pr.add_argument("--body", default=""); pr.add_argument("--kind", default="note")
    rv = sub.add_parser("reviews"); rv.add_argument("--json", action="store_true")
    rva = sub.add_parser("review"); rva.add_argument("action"); rva.add_argument("id")
    ds = sub.add_parser("desk"); dsub = ds.add_subparsers(dest="desk_cmd"); st = dsub.add_parser("start"); st.add_argument("kind"); st.add_argument("objective", nargs="?")
    sv = sub.add_parser("serve"); sv.add_argument("--host", default="127.0.0.1"); sv.add_argument("--port", type=int, default=8766)
    gr = sub.add_parser("graph"); grsub = gr.add_subparsers(dest="graph_cmd", required=True)
    grsub.add_parser("rebuild", help="Rebuild graph.json from wiki (folds type:→kind)")
    grsub.add_parser("enrich-kinds", help="Patch kinds from wiki type: without full rebuild")

    # Work coverage + named workspaces
    cov = sub.add_parser("coverage", help="Work-root coverage status and opt-out")
    covsub = cov.add_subparsers(dest="coverage_cmd", required=True)
    covsub.add_parser("status")
    co = covsub.add_parser("opt-out"); co.add_argument("path")
    ci = covsub.add_parser("opt-in"); ci.add_argument("path")

    ws = sub.add_parser("workspace", help="Named workspaces (e.g. biocure)")
    wsub = ws.add_subparsers(dest="workspace_cmd", required=True)
    wsub.add_parser("list")
    wu = wsub.add_parser("use"); wu.add_argument("name")
    wa = wsub.add_parser("add"); wa.add_argument("name"); wa.add_argument("path")

    wch = sub.add_parser("watch", help="Efficient Work-root watcher")
    wchsub = wch.add_subparsers(dest="watch_cmd", required=True)
    wo = wchsub.add_parser("once"); wo.add_argument("--confirm", action="store_true")
    wserve = wchsub.add_parser("serve")
    wserve.add_argument("--interval", type=float, default=3.0)
    wserve.add_argument("--debounce", type=float, default=2.5)
    wserve.add_argument("--confirm", action="store_true")

    priv = sub.add_parser("privacy"); priv.add_argument("path"); priv.add_argument("--json", action="store_true")

    args = p.parse_args(argv)
    if args.cmd == "setup":
        from . import paths, status, graph
        ws_path = Path(args.workspace).expanduser() if args.workspace else paths.default_workspace()
        root = paths.ensure_workspace(ws_path)
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
        return _print(ingest.ingest_path(args.path, confirm=bool(args.confirm)))
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
    if args.cmd == "graph":
        if args.graph_cmd == "rebuild":
            from . import graph
            data = graph.rebuild()
            return _print({"ok": True, "pages": data.get("pages"), "nodes": len(data.get("nodes") or []), "links": data.get("links")})
        if args.graph_cmd == "enrich-kinds":
            from . import atlas_ce
            return _print(atlas_ce.enrich_graph_kinds())
    if args.cmd == "coverage":
        from . import workroot
        if args.coverage_cmd == "status":
            return _print(workroot.coverage_status())
        if args.coverage_cmd == "opt-out":
            return _print(workroot.opt_out(args.path))
        if args.coverage_cmd == "opt-in":
            return _print(workroot.opt_in(args.path))
    if args.cmd == "workspace":
        from . import workroot
        if args.workspace_cmd == "list":
            return _print(workroot.list_workspaces())
        if args.workspace_cmd == "use":
            return _print(workroot.use_workspace(args.name))
        if args.workspace_cmd == "add":
            return _print(workroot.add_workspace(args.name, args.path))
    if args.cmd == "watch":
        from . import watch
        if args.watch_cmd == "once":
            return _print(watch.watch_once(confirm=bool(args.confirm)))
        if args.watch_cmd == "serve":
            return watch.watch_serve(
                interval=args.interval,
                debounce=args.debounce,
                confirm=bool(args.confirm),
            )
    if args.cmd == "privacy":
        from . import privacy_gate
        return _print(privacy_gate.scan_path(args.path), True)
    return 1
