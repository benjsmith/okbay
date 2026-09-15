"""get_page must not scan/parse the whole wiki on nested CE layouts."""
from __future__ import annotations
import json
import time
from pathlib import Path
import okbay.wiki as wiki


def _seed_nested(wiki_dir: Path, n_decoys: int = 50) -> Path:
    (wiki_dir / "sources").mkdir(parents=True)
    target = wiki_dir / "sources" / "email-beach-vacation-spots-98b0.md"
    target.write_text(
        "---\nstem: email-beach-vacation-spots-98b0\ntitle: Beach\ntype: source\n---\n\nHello [[ylvie-butler]]\n",
        encoding="utf-8",
    )
    for i in range(n_decoys):
        p = wiki_dir / "sources" / f"decoy-{i:03d}.md"
        p.write_text(
            f"---\nstem: decoy-{i:03d}\ntitle: D{i}\ntype: source\n---\n\nx\n",
            encoding="utf-8",
        )
    return target


def test_get_page_nested_stem(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    target = _seed_nested(wiki_dir)

    page = wiki.get_page("email-beach-vacation-spots-98b0", wiki_dir=wiki_dir)
    assert page is not None
    assert page.stem == "email-beach-vacation-spots-98b0"
    assert "Hello" in page.body
    assert page.path == target

    # second lookup hits cache
    page2 = wiki.get_page("email-beach-vacation-spots-98b0", wiki_dir=wiki_dir)
    assert page2 is not None
    assert page2.path == page.path


def test_warm_stem_index_then_fast_get(tmp_path: Path):
    wiki.invalidate_stem_index()
    wiki_dir = tmp_path / "wiki"
    _seed_nested(wiki_dir, n_decoys=80)

    status = wiki.warm_stem_index(wiki_dir)
    assert status["ok"] is True
    assert status["count"] >= 81

    t0 = time.perf_counter()
    for _ in range(20):
        page = wiki.get_page("email-beach-vacation-spots-98b0", wiki_dir=wiki_dir)
        assert page is not None
    elapsed = time.perf_counter() - t0
    # Local disk: 20 cached lookups should be well under a second.
    assert elapsed < 1.0, f"get_page after warm too slow: {elapsed:.3f}s"


def test_stem_index_persists_and_reloads(tmp_path: Path):
    wiki.invalidate_stem_index()
    ws = tmp_path / "ws"
    wiki_dir = ws / "wiki"
    _seed_nested(wiki_dir, n_decoys=10)

    status = wiki.warm_stem_index(wiki_dir)
    assert status["ok"]
    idx_path = ws / ".okbay" / "stem-index.json"
    assert idx_path.is_file()
    raw = json.loads(idx_path.read_text(encoding="utf-8"))
    assert "email-beach-vacation-spots-98b0" in raw["stems"]
    assert raw["count"] >= 11

    wiki.invalidate_stem_index()
    # Reload from disk without rebuilding via rglob (mtime matches).
    status2 = wiki.warm_stem_index(wiki_dir)
    assert status2["ok"]
    assert status2["count"] >= 11
    page = wiki.get_page("email-beach-vacation-spots-98b0", wiki_dir=wiki_dir)
    assert page is not None


def test_invalidate_on_workspace_switch_clears_index(tmp_path: Path):
    wiki.invalidate_stem_index()
    a = tmp_path / "a" / "wiki"
    b = tmp_path / "b" / "wiki"
    _seed_nested(a, n_decoys=5)
    (b / "sources").mkdir(parents=True)
    (b / "sources" / "other-page.md").write_text(
        "---\nstem: other-page\ntitle: Other\ntype: note\n---\n\ny\n",
        encoding="utf-8",
    )

    wiki.warm_stem_index(a)
    assert wiki.get_page("email-beach-vacation-spots-98b0", wiki_dir=a) is not None
    wiki.invalidate_stem_index()
    wiki.warm_stem_index(b)
    assert wiki.get_page("other-page", wiki_dir=b) is not None
    # Old stem should miss on the new wiki root.
    assert wiki.get_page("email-beach-vacation-spots-98b0", wiki_dir=b) is None
