"""Python fallback HTTP server."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import urlparse, parse_qs
from . import search, status, reviews, desks, ingest, graph, wiki

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, code, obj):
        raw = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/health": return self._json(200, {"ok": True, "daemon": "python"})
        if u.path == "/api/status": return self._json(200, status.snapshot())
        if u.path == "/api/search": return self._json(200, search.search(q.get("q", "")))
        if u.path == "/api/reviews": return self._json(200, {"reviews": reviews.list_reviews(q.get("state", "pending"))})
        if u.path in ("/atlas", "/api/theme"): return self._json(200, {"ok": True})
        self._json(404, {"error": "not found"})
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        u = urlparse(self.path)
        if u.path == "/api/ingest": return self._json(200, ingest.ingest_path(body["path"]))
        if u.path == "/api/propose": return self._json(200, reviews.propose(body.get("title",""), body.get("body",""), kind=body.get("kind","note")))
        if u.path == "/api/review": return self._json(200, reviews.resolve(body.get("id"), body.get("action","accept")))
        if u.path == "/api/desk/start": return self._json(200, desks.start(body.get("kind","curate"), body.get("objective","")))
        self._json(404, {"error": "not found"})

def serve(host="127.0.0.1", port=8766):
    httpd = ThreadingHTTPServer((host, port), H)
    print(f"okbay serve http://{host}:{port}")
    httpd.serve_forever()
