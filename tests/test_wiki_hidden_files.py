"""Hidden files such as macOS "._name.md" resource forks are not wiki pages."""
from pathlib import Path

from okbay import wiki


def test_list_pages_skips_hidden_and_undecodable_files(tmp_path: Path) -> None:
    wdir = tmp_path / "wiki"
    (wdir / "concepts").mkdir(parents=True)
    (wdir / "concepts" / "alpha.md").write_text("---\ntitle: Alpha\n---\nsee [[beta]]\n", encoding="utf-8")
    # AppleDouble companion written by macOS tar/cp on non-APFS volumes.
    (wdir / "concepts" / "._alpha.md").write_bytes(b"\x00\x05\x16\x07\x00\x02\x00\x00Mac OS X \xa3\xff")
    # A non-UTF-8 page must not take down the whole listing.
    (wdir / "concepts" / "latin1.md").write_bytes("caf\xe9 \xa3".encode("latin-1"))

    pages = wiki.list_pages(wdir)
    assert [p.stem for p in pages] == ["alpha"]
    assert "._alpha" not in wiki._build_stem_index(wdir)
