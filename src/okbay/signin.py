"""Find and re-show a pending grok sign-in inside Herdr panes.

grok's device sign-in prints a short code (for example ``ABCD-1234``) in the
pane it runs in and opens a "Device Sign-in" browser window. Both are easy to
lose behind other windows. ``okbay signin`` reads the Herdr panes, prints any
pending code, and with ``--focus`` brings the pane and sign-in window forward.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

CODE_RE = re.compile(r"\b([A-Z0-9]{4}-[A-Z0-9]{4})\b")
URL_RE = re.compile(r"https://\S+")
PENDING_MARKERS = ("Approve in your browser", "Waiting for approval", "Make sure your browser shows this code")
SIGNIN_TITLE_MARKERS = ("Device Sign-in", "Sign in")


def herdr_bin() -> str | None:
    found = shutil.which("herdr")
    if found:
        return found
    cand = Path.home() / ".local" / "bin" / "herdr"
    return str(cand) if cand.exists() else None


def _run(cmd: list[str], timeout: float = 5.0) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def parse_pane_text(text: str) -> dict:
    """Return {'pending': bool, 'code': str|None, 'url': str|None} for one pane."""
    pending = any(m in text for m in PENDING_MARKERS)
    code = None
    url = None
    if pending:
        codes = CODE_RE.findall(text)
        code = codes[-1] if codes else None
        urls = [u for u in URL_RE.findall(text) if "device" in u or "auth" in u or "login" in u]
        url = urls[-1] if urls else None
    return {"pending": pending, "code": code, "url": url}


def list_panes(herdr: str) -> list[dict]:
    raw = _run([herdr, "pane", "list"])
    try:
        return list((json.loads(raw).get("result") or {}).get("panes") or [])
    except Exception:
        return []


def read_pane(herdr: str, pane_id: str) -> str:
    return _run([herdr, "pane", "read", pane_id, "--source", "recent", "--lines", "200"])


def find_pending(herdr: str | None = None) -> list[dict]:
    herdr = herdr or herdr_bin()
    if not herdr:
        return []
    out = []
    for pane in list_panes(herdr):
        pid = pane.get("pane_id")
        if not pid:
            continue
        info = parse_pane_text(read_pane(herdr, pid))
        if info["pending"]:
            out.append({
                "pane_id": pid,
                "workspace_id": pane.get("workspace_id"),
                "cwd": pane.get("cwd"),
                **info,
            })
    return out


def _hypr_clients() -> list[dict]:
    try:
        return json.loads(_run(["hyprctl", "clients", "-j"]) or "[]")
    except Exception:
        return []


def _hypr_focus_window(addr: str) -> None:
    _run(["hyprctl", "dispatch", f'hl.dsp.focus({{ window = "address:{addr}" }})'])


def focus(pending: list[dict], herdr: str | None = None) -> list[str]:
    """Bring the Herdr window, the pending pane, and any sign-in browser window forward."""
    herdr = herdr or herdr_bin()
    done = []
    if pending and herdr:
        ws = pending[0].get("workspace_id")
        if ws:
            _run([herdr, "workspace", "focus", ws])
            done.append(f"herdr workspace {ws}")
    if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and not shutil.which("hyprctl"):
        return done
    clients = _hypr_clients()
    herdr_win = next((c for c in clients if (c.get("class") or "").lower() == "herdr"), None)
    signin_win = next((c for c in clients
                       if any(m in (c.get("title") or "") for m in SIGNIN_TITLE_MARKERS)
                       and "chrom" in (c.get("class") or "").lower()), None)
    for win, name in ((herdr_win, "herdr window"), (signin_win, "sign-in window")):
        if win and win.get("address"):
            _hypr_focus_window(win["address"])
            done.append(name)
    return done


def restart_login(pane_id: str, herdr: str | None = None) -> bool:
    """Start a fresh `grok login` in a pane (only when nothing is pending)."""
    herdr = herdr or herdr_bin()
    if not herdr:
        return False
    return subprocess.run([herdr, "pane", "run", pane_id, "grok login"],
                          capture_output=True, text=True).returncode == 0


def main(args) -> int:
    herdr = herdr_bin()
    if not herdr:
        print("Herdr is not installed, so there is no grok pane to check.")
        return 1
    pending = find_pending(herdr)
    if getattr(args, "json", False):
        print(json.dumps({"pending": pending}, indent=2))
    elif pending:
        for p in pending:
            print(f"grok is waiting for sign-in in Herdr pane {p['pane_id']} ({p.get('cwd') or ''})")
            print(f"  code: {p.get('code') or '(not shown in the pane)'}")
            if p.get("url"):
                print(f"  url:  {p['url']}")
    else:
        print("No grok sign-in is waiting in any Herdr pane.")
    if getattr(args, "focus", False) and pending:
        moved = focus(pending, herdr)
        if moved and not getattr(args, "json", False):
            print("Brought forward: " + ", ".join(moved))
    if getattr(args, "restart", None):
        if pending:
            print("A sign-in is already waiting; not starting another.")
        elif restart_login(args.restart, herdr):
            print(f"Started grok login in pane {args.restart}. Run `okbay signin` to see the code.")
        else:
            print(f"Could not start grok login in pane {args.restart}.")
            return 1
    return 0
