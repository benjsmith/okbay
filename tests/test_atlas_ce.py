"""Slice 0: CE Atlas data bridge shape checks."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("OKBAY_WORKSPACE", str(Path("/tmp/okbay-atlas-ce-ws")))
os.environ.setdefault("XDG_STATE_HOME", str(Path("/tmp/okbay-atlas-ce-state")))

from okbay import atlas_ce, paths, theme  # noqa: E402


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    root = paths.ensure_workspace()
    wiki = paths.wiki(root)
    # Synthetic CE-ish pages: type: frontmatter + kind + wikilinks + a source file edge.
    (wiki / "alpha.md").write_text(
        "---\nstem: alpha\ntitle: Alpha Concept\ntype: concept\n---\n\nSee [[beta]] and [[missing-page]].\n",
        encoding="utf-8",
    )
    (wiki / "beta.md").write_text(
        "---\nstem: beta\ntitle: Beta Note\nkind: note\nsources: [vault/a.pdf]\n---\n\nBack to [[alpha]].\n",
        encoding="utf-8",
    )
    (wiki / "concepts.md").write_text(
        "---\nstem: concepts\ntitle: Concepts Hub\nkind: hub\n---\n\nIndex.\n",
        encoding="utf-8",
    )
    return root


def test_build_ce_data_shape(ws):
    from okbay import graph

    g = graph.build_graph(ws)
    # Python graph adds extracted_from → file: edges; bridge must drop them.
    assert any(str(e.get("target", "")).startswith("file:") for e in g["edges"])

    data = atlas_ce.build_ce_data(graph=g, ws=ws)  # kind already folded from type: at graph build
    assert "workspace" in data and data["workspace"]
    assert "generated_at" in data and "T" in data["generated_at"]
    assert isinstance(data["palette"], dict) and len(data["palette"]) > 0
    assert "concept" in data["palette"] or "note" in data["palette"]
    assert isinstance(data["nodes"], list) and data["nodes"]
    assert isinstance(data["edges"], list)
    assert isinstance(data["pages"], dict)
    assert isinstance(data["page_count"], int)
    assert data["page_count"] == g["pages"]

    for n in data["nodes"]:
        assert not str(n["id"]).startswith("file:")
        assert set(n) >= {"id", "path", "type", "title", "degree"}
        assert isinstance(n["degree"], int)

    for e in data["edges"]:
        assert not str(e["source"]).startswith("file:")
        assert not str(e["target"]).startswith("file:")
        assert "type" in e

    # alpha should pick up CE frontmatter type: concept
    alpha = next(n for n in data["nodes"] if n["id"] == "alpha")
    assert alpha["type"] == "concept"
    assert alpha["degree"] >= 1

    # pages map stubs
    assert data["pages"]["alpha"]["body_html"] == ""
    assert "sources" in data["pages"]["beta"]["properties"]

    # Degree sanity: sum of degrees == 2 * non-file edges (undirected count per endpoint)
    deg_sum = sum(n["degree"] for n in data["nodes"])
    assert deg_sum == 2 * len(data["edges"])


def test_canonical_type_plurals():
    assert atlas_ce.canonical_type("concepts") == "concept"
    assert atlas_ce.canonical_type("SOURCES") == "source"
    assert atlas_ce.canonical_type("todo") == "todo-list"
    assert atlas_ce.canonical_type("unclassified", "[con] Foo") == "concept"
    assert atlas_ce.normalize_id("foo.md") == "foo"


def test_http_atlas_data(ws, monkeypatch):
    """Reproducible curl-equivalent against the in-process handler transform."""
    from okbay import graph

    graph.build_graph(ws)
    data = atlas_ce.load_ce(ws)
    assert data["page_count"] >= 3
    assert theme.type_palette()  # palette source non-empty
    # Documented curl example target shape:
    #   curl -s http://127.0.0.1:8766/api/atlas/data | jq '{workspace,page_count,nodes:(.nodes|length),palette:(.palette|keys)}'
    sample = data["nodes"][:3]
    assert all("type" in n and "degree" in n for n in sample)


def test_markdown_to_html_basic():
    from okbay import wiki

    html = wiki.markdown_to_html("# Hello\n\nSee [[alpha|Alpha]] and **bold**.\n")
    assert "<h1>" in html and "Hello" in html
    assert 'data-page="alpha"' in html
    assert "<strong>bold</strong>" in html


def test_atlas_page_payload(ws):
    from okbay import wiki, paths

    payload = wiki.page_payload("alpha", wiki_dir=paths.wiki(ws))
    assert payload is not None
    assert payload["id"] == "alpha"
    assert payload["title"] == "Alpha Concept"
    assert payload["type"] == "concept"
    assert "[[beta]]" in payload["markdown"] or "beta" in payload["body_html"]
    assert "body_html" in payload and payload["body_html"]
    # Must not invent empty stubs for missing pages
    assert wiki.page_payload("no-such-page", wiki_dir=paths.wiki(ws)) is None


def test_http_atlas_page(ws, monkeypatch):
    """Exercise GET /api/atlas/page via the request handler."""
    from okbay import graph, server
    from io import BytesIO
    from urllib.parse import urlparse

    graph.build_graph(ws)

    class Fake:
        def __init__(self, path):
            self.path = path
            self.headers = {}
            self.wfile = BytesIO()
            self._code = None
            self._headers = {}

        def send_response(self, code):
            self._code = code

        def send_header(self, k, v):
            self._headers[k] = v

        def end_headers(self):
            pass

        def log_message(self, *a):
            pass

    h = Fake("/api/atlas/page?stem=alpha")
    # Bind methods from Handler
    h._json = server.Handler._json.__get__(h, Fake)
    h.do_GET = server.Handler.do_GET.__get__(h, Fake)
    h.do_GET()
    assert h._code == 200
    import json
    body = json.loads(h.wfile.getvalue().decode())
    assert body["stem"] == "alpha"
    assert body["body_html"]

    missing = Fake("/api/atlas/page?stem=does-not-exist")
    missing._json = server.Handler._json.__get__(missing, Fake)
    missing.do_GET = server.Handler.do_GET.__get__(missing, Fake)
    missing.do_GET()
    assert missing._code == 404


def test_enrich_graph_kinds_and_files(ws):
    from okbay import atlas_ce, graph

    g = graph.build_graph(ws)
    # Stale kind: note despite type: concept in wiki
    for n in g["nodes"]:
        if n["id"] == "alpha":
            n["kind"] = "note"
    import json
    from okbay import paths
    paths.graph_json(ws).write_text(json.dumps(g), encoding="utf-8")

    result = atlas_ce.enrich_graph_kinds(ws)
    assert result["ok"] and result["changed"] >= 1
    data = atlas_ce.build_ce_data(ws=ws)
    alpha = next(n for n in data["nodes"] if n["id"] == "alpha")
    assert alpha["type"] == "concept"
    # files/sources present on pages stubs
    assert "files" in data["pages"]["beta"]["properties"]
    assert "sources" in data["pages"]["beta"]["properties"]


def test_theme_palette_has_core_types():
    from okbay import theme

    pal = theme.type_palette()
    for key in ("concept", "entity", "evidence", "analysis", "source", "table", "note"):
        assert key in pal
        assert pal[key].startswith("#")


def test_locate_reveal_flag(ws, monkeypatch):
    from okbay import locate
    monkeypatch.setenv("OKBAY_REVEAL", "1")
    # resolve-only
    doc = locate.locate("alpha", reveal=False)
    assert doc["ok"] is True
    assert doc.get("revealed") is None
    assert "wiki" in doc
