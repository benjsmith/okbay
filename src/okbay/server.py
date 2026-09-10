"""Tiny HTTP front for Atlas + JSON API on :8766."""
from __future__ import annotations
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from . import __version__, desks, graph, ingest, locate, paths, reviews, search, status, theme, wiki

def _atlas_html() -> str:
    path = Path(__file__).resolve().parent / "static" / "atlas.html"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "<!doctype html><title>OKBay Atlas</title><p>atlas.html missing</p>"

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
    def _html(self, text, code=200):
        body = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        path = u.path
        if path in ("/", "/atlas"):
            return self._html(_atlas_html())
        if path in ("/theme", "/api/theme"):
            return self._json(theme.resolve())
        if path == "/health":
            return self._json({"ok": True, "version": __version__, "daemon": "python"})
        if path == "/api/status":
            return self._json(status.snapshot())
        if path in ("/api/graph", "/graph"):
            return self._json(graph.load())
        if path in ("/api/search", "/atlas/search"):
            return self._json(search.search(q.get("q", [""])[0]))
        if path == "/api/reviews":
            return self._json({"reviews": reviews.list_reviews(q.get("state", ["pending"])[0])})
        if path == "/api/desk":
            return self._json(desks.status())
        if path == "/api/locate":
            return self._json(locate.locate(q.get("stem", [""])[0]))
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
        if path == "/api/rebuild":
            return self._json(graph.rebuild())
        if path == "/api/ingest":
            return self._json(ingest.ingest_path(body.get("path") or body.get("src") or ""))
        if path == "/api/propose":
            return self._json(reviews.propose(body.get("title") or "untitled", body.get("body") or "", kind=body.get("kind") or "note", reason=body.get("reason") or ""))
        if path == "/api/review":
            return self._json(reviews.resolve(body.get("id") or "", body.get("action") or "reject", note=body.get("note") or ""))
        if path == "/api/desk/start":
            return self._json(desks.start(body.get("kind") or "curate", objective=body.get("objective") or ""))
        if path == "/api/desk/stop":
            return self._json(desks.stop(body.get("kind")))
        return self._json({"error": "not found"}, 404)

def main(port: int = 8766, host: str = "127.0.0.1") -> int:
    paths.ensure_workspace()
    status.snapshot()
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"okbayd listening on http://{host}:{port} workspace={paths.workspace()}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0

def serve(host: str = "127.0.0.1", port: int = 8766) -> int:
    return main(port=port, host=host)
