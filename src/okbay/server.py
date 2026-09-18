"""Tiny HTTP front for Atlas + JSON API on :8766."""
from __future__ import annotations
import json
import mimetypes
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse, unquote
from . import __version__, atlas_ce, desks, graph, ingest, locate, paths, reviews, search, status, theme, viewer_mutex, views, wiki

_STATIC_ROOT = Path(__file__).resolve().parent / "static"

def _atlas_html() -> str:
    path = _STATIC_ROOT / "atlas.html"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "<!doctype html><title>OKBay Atlas</title><p>atlas.html missing</p>"

def _safe_static(rel: str) -> Path | None:
    """Resolve /static/... under package static/; reject traversal."""
    rel = unquote(rel).lstrip("/")
    if not rel or ".." in rel.split("/"):
        return None
    target = (_STATIC_ROOT / rel).resolve()
    try:
        target.relative_to(_STATIC_ROOT.resolve())
    except ValueError:
        return None
    return target if target.is_file() else None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return
    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _html(self, text, code=200, *, csp: str | None = None):
        body = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if csp:
            self.send_header("Content-Security-Policy", csp)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _file(self, path: Path, code=200):
        data = path.read_bytes()
        ctype, _ = mimetypes.guess_type(str(path))
        if not ctype:
            if path.suffix == ".js":
                ctype = "application/javascript"
            elif path.suffix == ".css":
                ctype = "text/css"
            else:
                ctype = "application/octet-stream"
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=60")
        self.end_headers()
        self.wfile.write(data)
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        path = u.path
        # Charter #3: QML active ⇒ HTML atlas /views hosts off (JSON API stays).
        if viewer_mutex.should_block_html_ui(path):
            accept = (self.headers.get("Accept") or "").lower()
            if "application/json" in accept:
                return self._json(viewer_mutex.blocked_payload(path), 409)
            return self._html(viewer_mutex.blocked_html_stub(path), 409)
        if path in ("/", "/atlas"):
            return self._html(_atlas_html())
        # Vendor + other atlas static assets (knowledge-atlas.js, fuse, …).
        if path.startswith("/static/"):
            f = _safe_static(path[len("/static/"):])
            if f is None:
                return self._json({"error": "not found"}, 404)
            return self._file(f)
        if path in ("/theme", "/api/theme"):
            return self._json(theme.resolve())
        if path == "/health":
            return self._json({"ok": True, "version": __version__, "daemon": "python"})
        if path == "/api/status":
            return self._json(status.snapshot())
        if path == "/api/viewer":
            return self._json(viewer_mutex.snapshot())
        if path in ("/api/graph", "/graph"):
            return self._json(graph.load())
        # CE Atlas data bridge (CuriosityDataSource / CEData shape). See atlas_ce.py.
        if path in ("/api/atlas/data", "/atlas/data"):
            return self._json(atlas_ce.load_ce())
        if path in ("/api/search", "/atlas/search"):
            return self._json(search.search(q.get("q", [""])[0]))
        if path == "/api/reviews":
            return self._json({"reviews": reviews.list_reviews(q.get("state", ["pending"])[0])})
        if path == "/api/desk":
            return self._json(desks.status())
        # Accept /locate alias and both stem= / q= (atlas.html historically used ?q=).
        if path in ("/api/locate", "/locate"):
            stem = (q.get("stem") or q.get("q") or [""])[0]
            rev = (q.get("reveal") or ["1"])[0].lower()
            reveal = rev not in ("0", "false", "no", "off")
            return self._json(locate.locate(stem, reveal=reveal))
        # Slice 2: lazy wiki page for atlas modal (no body_html in /api/atlas/data).
        if path in ("/api/atlas/page", "/atlas/page"):
            stem = (q.get("stem") or q.get("q") or q.get("id") or [""])[0]
            payload = wiki.page_payload(stem) if stem else None
            if payload is None:
                return self._json({"error": "not found", "stem": stem}, 404)
            return self._json(payload)
        # Viewer source mode: vault file body (sandboxed under workspace vault/).
        if path in ("/api/atlas/source", "/atlas/source"):
            spath = (q.get("path") or [""])[0]
            ssrc = (q.get("source") or [""])[0]
            stem = (q.get("stem") or [""])[0]
            try:
                payload = wiki.source_payload(path=spath, source=ssrc, stem=stem)
            except ValueError as e:
                return self._json({"error": str(e), "kind": "source"}, 400)
            if payload is None:
                return self._json(
                    {"error": "not found", "path": spath or ssrc, "stem": stem, "kind": "source"},
                    404,
                )
            return self._json(payload)
        if path.startswith("/api/wiki/") or path.startswith("/wiki/"):
            stem = unquote(path.rsplit("/", 1)[-1]).strip()
            payload = wiki.page_payload(stem) if stem else None
            if payload is None:
                return self._json({"error": "not found", "stem": stem}, 404)
            return self._json(payload)
        if path in ("/api/workspace", "/api/workspace/list"):
            from . import workroot
            return self._json(workroot.list_workspaces())
        if path == "/api/views":
            return self._json(views.list_views())
        if path == "/api/views/pages":
            try:
                limit = int((q.get("limit") or ["5000"])[0])
            except ValueError:
                limit = 5000
            return self._json(views.pages_table(limit=max(1, min(limit, 50000))))
        if path.startswith("/api/views/"):
            vid = unquote(path[len("/api/views/"):].strip("/"))
            if "/" in vid or not vid:
                return self._json({"error": "not found"}, 404)
            item = views.get_view(vid)
            if item is None:
                return self._json({"error": "not found", "id": vid}, 404)
            return self._json({"ok": True, "view": item})
        # Sandboxed dynamic HTML decks (iframe src). Tight CSP; no parent access.
        if path.startswith("/views/"):
            vid = unquote(path[len("/views/"):].strip("/"))
            if "/" in vid or not vid:
                return self._json({"error": "not found"}, 404)
            html = views.view_html(vid)
            if html is None:
                item = views.get_view(vid)
                if item and item.get("url") and not str(item["url"]).startswith("/views/"):
                    return self._json({"ok": True, "redirect": item["url"], "view": item})
                return self._json({"error": "not found", "id": vid}, 404)
            csp = (
                "default-src 'none'; img-src data: https: http:; "
                "style-src 'unsafe-inline'; font-src data:; "
                "script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; "
                "frame-ancestors 'self'"
            )
            return self._html(html, csp=csp)
        return self._json({"error": "not found"}, 404)
    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode() or "{}")
        except json.JSONDecodeError:
            return {}
    def do_POST(self):
        body = self._body()
        path = urlparse(self.path).path
        if path == "/api/viewer":
            try:
                return self._json(viewer_mutex.set_mode(
                    body.get("mode") or body.get("viewer_mode") or "",
                    source="api",
                ))
            except ValueError as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
        if path == "/api/rebuild":
            return self._json(graph.rebuild())
        if path == "/api/atlas/enrich-kinds":
            return self._json(atlas_ce.enrich_graph_kinds())
        if path == "/api/ingest":
            confirm = bool(body.get("confirm"))
            return self._json(ingest.ingest_path(body.get("path") or body.get("src") or "", confirm=confirm))
        if path in ("/api/privacy/scan", "/api/privacy"):
            from . import privacy_gate
            return self._json(privacy_gate.scan_path(body.get("path") or body.get("src") or ""))
        if path == "/api/coverage":
            from . import workroot
            return self._json(workroot.coverage_status())
        if path in ("/api/workspace/list",):
            from . import workroot
            return self._json(workroot.list_workspaces())
        if path == "/api/workspace/use":
            from . import workroot
            try:
                return self._json(workroot.use_workspace(body.get("name") or body.get("workspace") or ""))
            except KeyError as exc:
                return self._json({"ok": False, "error": str(exc)}, 404)
            except ValueError as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
        if path == "/api/workspace/add":
            from . import workroot
            try:
                return self._json(workroot.add_workspace(
                    body.get("name") or "",
                    body.get("path") or body.get("src") or "",
                ))
            except ValueError as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
        if path == "/api/workspace/split":
            from . import workroot
            paths_in = body.get("paths") or body.get("path") or []
            if isinstance(paths_in, str):
                paths_in = [paths_in]
            try:
                return self._json(workroot.split_workspace(
                    body.get("name") or "",
                    paths_in,
                    hub=body.get("hub"),
                ))
            except (ValueError, KeyError) as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
        if path == "/api/propose":
            return self._json(reviews.propose(body.get("title") or "untitled", body.get("body") or "", kind=body.get("kind") or "note", reason=body.get("reason") or ""))
        if path == "/api/review":
            return self._json(reviews.resolve(body.get("id") or "", body.get("action") or "reject", note=body.get("note") or ""))
        if path == "/api/desk/start":
            return self._json(desks.start(body.get("kind") or "curate", objective=body.get("objective") or ""))
        if path == "/api/desk/stop":
            return self._json(desks.stop(body.get("kind")))
        if path == "/api/views":
            try:
                return self._json(views.publish_view(
                    body.get("id") or "",
                    title=body.get("title") or "",
                    html=body.get("html"),
                    url=body.get("url"),
                    workspace=body.get("workspace"),
                    ephemeral=bool(body.get("ephemeral")),
                ))
            except ValueError as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
        if path == "/api/reviews/accept-all":
            return self._json(views.accept_all_reviews())
        return self._json({"error": "not found"}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/views/"):
            vid = unquote(path[len("/api/views/"):].strip("/"))
            if "/" in vid or not vid:
                return self._json({"error": "not found"}, 404)
            try:
                return self._json(views.delete_view(vid))
            except KeyError as exc:
                return self._json({"ok": False, "error": str(exc)}, 404)
            except ValueError as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
        return self._json({"error": "not found"}, 404)

def main(port: int = 8766, host: str = "127.0.0.1") -> int:
    paths.ensure_workspace()
    status.snapshot()
    # Warm stem→path index in background so /health is immediate but first
    # /api/atlas/page is O(1) after the index lands (critical on 9p / Biocure).
    wiki.warm_stem_index_background()
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"okbayd listening on http://{host}:{port} workspace={paths.workspace()}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0

def serve(host: str = "127.0.0.1", port: int = 8766) -> int:
    return main(port=port, host=host)
