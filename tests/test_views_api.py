"""Views API + stem warm wiring."""
from __future__ import annotations
from pathlib import Path
import json
import os
import threading
from http.client import HTTPConnection

import okbay.views as views
import okbay.wiki as wiki
from okbay import paths


def test_publish_list_delete_view(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws"))
    paths.ensure_workspace(tmp_path / "ws")
    out = views.publish_view("deck-demo", title="Demo", html="<h1>Hi</h1>", ephemeral=True)
    assert out["ok"]
    listed = views.list_views(include_reviews_when_empty=True)
    ids = [v["id"] for v in listed["views"]]
    assert "atlas" in ids and "viewer" in ids and "deck-demo" in ids
    assert views.view_html("deck-demo") == "<h1>Hi</h1>"
    assert views.delete_view("deck-demo")["ok"]
    assert views.get_view("deck-demo") is None


def test_builtin_reviews_hidden_when_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws2"))
    paths.ensure_workspace(tmp_path / "ws2")
    listed = views.list_views()
    ids = [v["id"] for v in listed["views"]]
    assert "reviews" not in ids or listed.get("pending_reviews", 0) > 0


def test_warm_stem_index_exportable(tmp_path: Path):
    wiki.invalidate_stem_index()
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "a.md").write_text("---\nstem: a\ntitle: A\n---\n\nx\n", encoding="utf-8")
    status = wiki.warm_stem_index(wiki_dir)
    assert status["ok"] and status["count"] >= 1
