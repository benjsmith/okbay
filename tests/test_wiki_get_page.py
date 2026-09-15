"""get_page must not scan/parse the whole wiki on nested CE layouts."""
from __future__ import annotations
from pathlib import Path
import okbay.wiki as wiki


def test_get_page_nested_stem(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    (wiki_dir / "sources").mkdir(parents=True)
    target = wiki_dir / "sources" / "email-beach-vacation-spots-98b0.md"
    target.write_text(
        "---\nstem: email-beach-vacation-spots-98b0\ntitle: Beach\ntype: source\n---\n\nHello [[ylvie-butler]]\n",
        encoding="utf-8",
    )
    # decoy flat miss + many siblings would previously force list_pages()
    for i in range(50):
        p = wiki_dir / "sources" / f"decoy-{i:03d}.md"
        p.write_text(f"---\nstem: decoy-{i:03d}\ntitle: D{i}\ntype: source\n---\n\nx\n", encoding="utf-8")

    page = wiki.get_page("email-beach-vacation-spots-98b0", wiki_dir=wiki_dir)
    assert page is not None
    assert page.stem == "email-beach-vacation-spots-98b0"
    assert "Hello" in page.body

    # second lookup hits cache
    page2 = wiki.get_page("email-beach-vacation-spots-98b0", wiki_dir=wiki_dir)
    assert page2 is not None
    assert page2.path == page.path
