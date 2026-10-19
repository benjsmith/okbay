from okbay import signin

PANE = """
          Approve in your browser to finish signing in.

                       SABB-TS8R

          Make sure your browser shows this code.
          Waiting for approval...
"""


def test_parse_pending_code():
    info = signin.parse_pane_text(PANE)
    assert info["pending"] and info["code"] == "SABB-TS8R"


def test_parse_idle_pane_ignores_code_like_text():
    info = signin.parse_pane_text("build ABCD-1234 ok\n$ ")
    assert info == {"pending": False, "code": None, "url": None}


def test_find_pending(monkeypatch):
    monkeypatch.setattr(signin, "list_panes", lambda h: [
        {"pane_id": "wA:p1", "workspace_id": "wA", "cwd": "/a"},
        {"pane_id": "wB:p1", "workspace_id": "wB", "cwd": "/b"},
    ])
    monkeypatch.setattr(signin, "read_pane", lambda h, pid: PANE if pid == "wB:p1" else "$ ")
    got = signin.find_pending("herdr")
    assert [p["pane_id"] for p in got] == ["wB:p1"] and got[0]["code"] == "SABB-TS8R"


def test_cli_has_signin():
    import pytest
    from okbay import cli
    with pytest.raises(SystemExit):
        cli.main(["signin", "--help"])
