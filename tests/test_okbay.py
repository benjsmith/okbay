import json
import os
from pathlib import Path

import pytest

os.environ["OKBAY_WORKSPACE"] = str(Path("/tmp/okbay-test-ws"))
os.environ["XDG_STATE_HOME"] = str(Path("/tmp/okbay-test-state"))

from okbay import paths, wiki, graph, ingest, reviews, desks, status, search  # noqa: E402


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("OKBAY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return paths.ensure_workspace()


def test_setup_and_ingest(ws):
    src = ws / "drop.txt"
    src.write_text("The landlord requires two months deposit.\n")
    result = ingest.ingest_path(src)
    assert result.get("ok") is True
    pages = wiki.list_pages()
    assert any(p.kind in {"source", "source-note"} for p in pages)
    g = graph.rebuild()
    assert g["pages"] >= 1
    hits = search.search("deposit")
    assert hits["count"] >= 1


def test_propose_review(ws):
    rec = reviews.propose("Deposit rule", "Two months deposit. [[source-drop]]", kind="fact")
    assert rec["status"] == "pending"
    listed = reviews.list_reviews()
    assert listed
    reviews.resolve(rec["id"], "accept")
    page = wiki.get_page("deposit-rule")
    assert page is not None
    assert "Two months" in page.body


def test_desk(ws):
    desk = desks.start("curate", "densify")
    assert desk["id"] == "curate"
    snap = status.snapshot()
    assert snap["desk"]["id"] == "curate"
