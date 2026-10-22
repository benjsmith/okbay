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


def _capture(monkeypatch, clients):
    sent = []
    monkeypatch.setattr(signin, "_hypr_clients", lambda: clients)
    monkeypatch.setattr(signin, "_run", lambda cmd, timeout=5.0: sent.append(cmd[2]) or "")
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "test")
    return sent


SIGNIN_TILED = {"address": "0xs", "class": "chromium", "floating": False,
                "title": "Device Sign-in | SpaceXAI Accounts - Chromium"}
HERDR = {"address": "0xh", "class": "herdr", "floating": True, "title": "omarchy: biocure"}


def test_focus_floats_and_raises_tiled_signin_window(monkeypatch):
    sent = _capture(monkeypatch, [HERDR, SIGNIN_TILED])
    done = signin.focus([], herdr="")
    assert done == ["herdr window", "sign-in window"]
    assert sent == [
        'hl.dsp.focus({ window = "address:0xh" })',
        'hl.dsp.window.float({ action = "toggle", window = "address:0xs" })',
        'hl.dsp.window.resize({ x = 960, y = 760, relative = false, window = "address:0xs" })',
        'hl.dsp.window.center({ window = "address:0xs" })',
        'hl.dsp.focus({ window = "address:0xs" })',
        'hl.dsp.window.bring_to_top({ window = "address:0xs" })',
    ]


def test_focus_leaves_floating_signin_window_floating(monkeypatch):
    sent = _capture(monkeypatch, [dict(SIGNIN_TILED, floating=True)])
    signin.focus([], herdr="")
    assert not any("float(" in s for s in sent)
    assert sent[-1] == 'hl.dsp.window.bring_to_top({ window = "address:0xs" })'


def test_other_sign_in_pages_are_not_touched(monkeypatch):
    sent = _capture(monkeypatch, [{"address": "0xg", "class": "chromium", "floating": False,
                                   "title": "Sign in - Google Accounts - Chromium"}])
    assert signin.focus([], herdr="") == []
    assert sent == []
