#!/usr/bin/env python3
"""Place Atlas/Nautilus/Herdr/okstratr into a 2x2 grid on WS_TARGET.

Hardened for Omarchy Hyprland 0.56 Lua dispatchers (hl.dsp.*) — classic
`hyprctl dispatch workspace N` fails with: error: ')' expected.

Also hardened for OkbayAtlas windowrules (float+fullscreen) and Quickshell
FloatingWindow okstratr (title Okstratr / class quickshell|qs).

Layout (monitor coords, top bar reserved):
  TL Atlas | TR Nautilus
  BL Herdr | BR okstratr
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

WS = os.environ.get("WS_TARGET") or "2"
LOG = os.environ.get("OKBAY_FULL_PRODUCT_LOG") or "/tmp/okbay-full-product.log"
ROLES = ("atlas", "nautilus", "herdr", "okstratr")
# Omarchy top bar ~26–40px; prefer monitor.reserved[1] when present.
DEFAULT_TOP_BAR = int(os.environ.get("OKBAY_TOP_BAR") or "32")


def log(*parts):
    line = " ".join(str(p) for p in parts)
    print(line, flush=True)
    # Avoid double-write when caller already redirects stdout to LOG
    # (okbay-open-full-product.sh historically did `python3 helper >>$LOG`).
    try:
        out_real = os.path.realpath("/proc/self/fd/1")
        log_real = os.path.realpath(LOG)
        if out_real == log_real:
            return
    except OSError:
        pass
    try:
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def ensure_hypr_env():
    """Export XDG_RUNTIME_DIR + HYPRLAND_INSTANCE_SIGNATURE for SSH/script cases."""
    if not os.environ.get("XDG_RUNTIME_DIR"):
        try:
            uid = os.getuid()
        except Exception:
            uid = 1000
        os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return
    hypr = Path(os.environ["XDG_RUNTIME_DIR"]) / "hypr"
    try:
        sigs = sorted(p.name for p in hypr.iterdir() if p.is_dir())
    except OSError:
        sigs = []
    if sigs:
        os.environ["HYPRLAND_INSTANCE_SIGNATURE"] = sigs[0]
        log("HYPRLAND_INSTANCE_SIGNATURE", sigs[0])


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    return (r.stdout or "") + (r.stderr or "")


def dsp(lua: str):
    """Dispatch an Omarchy Lua hl.dsp.* expression (never bare classic forms)."""
    out = run(["hyprctl", "dispatch", lua]).strip()
    log("DSP", lua[:160], "->", out[:120])
    return out


def clients():
    try:
        return json.loads(subprocess.check_output(["hyprctl", "clients", "-j"], text=True))
    except Exception as e:
        log("clients err", e)
        return []


def mon():
    try:
        mons = json.loads(subprocess.check_output(["hyprctl", "monitors", "-j"], text=True))
        for m in mons:
            if m.get("focused"):
                return m
        return mons[0]
    except Exception:
        return {"width": 1920, "height": 1080, "x": 0, "y": 0, "reserved": [0, 0, 0, 0]}


def blob(c):
    cls = c.get("class")
    if isinstance(cls, list):
        classes = " ".join(str(x) for x in cls)
    else:
        classes = str(cls or "")
    parts = [
        classes,
        str(c.get("initialClass") or ""),
        str(c.get("title") or ""),
        str(c.get("initialTitle") or ""),
    ]
    return " ".join(parts).lower()


def class_str(c):
    cls = c.get("class")
    if isinstance(cls, list):
        return " ".join(str(x) for x in cls).lower()
    return str(cls or "").lower()


def classify(c):
    """Return role name or None. FloatingWindow okstratr is Quickshell."""
    b = blob(c)
    title = str(c.get("title") or "").lower()
    initial = str(c.get("initialTitle") or "").lower()
    cls = class_str(c)
    initial_cls = str(c.get("initialClass") or "").lower()

    # Atlas: prefer --class=OkbayAtlas; Omarchy Chromium often ignores --class and
    # reports Wayland app_id like chrome-127.0.0.1__atlas-Default.
    if "okbayatlas" in b or "okbayatlas" in cls or "okbayatlas" in initial_cls:
        return "atlas"
    if "8766/atlas" in b or "8766/atlas" in title or "8766/atlas" in initial:
        return "atlas"
    # chrome-<host>__atlas-* / chrome-*8766* / title hosts atlas URL
    if cls.startswith("chrome-") or initial_cls.startswith("chrome-"):
        chrome_blob = f"{cls} {initial_cls} {title} {initial}"
        if (
            "atlas" in chrome_blob
            or "8766" in chrome_blob
            or ("127.0.0.1" in chrome_blob and "atlas" in b)
        ):
            return "atlas"
    if ("atlas" in b and ("chromium" in b or "chrome" in b)):
        return "atlas"

    # Nautilus
    if "nautilus" in b or "org.gnome.nautilus" in b:
        return "nautilus"

    # Herdr terminal
    if "herdr" in b:
        return "herdr"

    # okstratr — QML FloatingWindow (title Okstratr) under Quickshell
    if title == "okstratr" or initial == "okstratr":
        return "okstratr"
    if "okstratr" in b or "benjsmith.okstratr" in b:
        return "okstratr"
    if "quickshell" in b and ("okstratr" in b or "desk" in b or "panel" in b):
        return "okstratr"
    # FloatingWindow often reports class qs / quickshell with empty-ish title until map
    if c.get("floating") and (
        cls in ("qs", "quickshell")
        or initial_cls in ("qs", "quickshell")
        or "quickshell" in cls
        or "quickshell" in initial_cls
    ):
        # Prefer larger floating Quickshell surfaces (desk panel, not tiny popups)
        size = c.get("size") or [0, 0]
        try:
            w, h = int(size[0] or 0), int(size[1] or 0)
        except Exception:
            w = h = 0
        if w >= 400 and h >= 300:
            return "okstratr_maybe"
        return "okstratr_maybe"
    return None


def wait_roles(timeout=14.0):
    deadline = time.time() + timeout
    best = {}
    while time.time() < deadline:
        found = {}
        maybes = []
        for c in clients():
            role = classify(c)
            if role == "okstratr_maybe":
                maybes.append(c)
                continue
            if role and role not in found:
                found[role] = c
        if "okstratr" not in found and maybes:
            # Prefer title match, then largest area, then focus history
            def score(c):
                title = str(c.get("title") or "").lower()
                size = c.get("size") or [0, 0]
                try:
                    area = int(size[0] or 0) * int(size[1] or 0)
                except Exception:
                    area = 0
                title_hit = 1 if "okstratr" in title else 0
                return (title_hit, area, -(c.get("focusHistoryID") or 0))

            maybes.sort(key=score, reverse=True)
            found["okstratr"] = maybes[0]
        best = found
        if all(k in found for k in ROLES):
            return found
        time.sleep(0.25)
    return best


def is_atlas_client(c):
    return classify(c) == "atlas"


def focus_window(addr: str):
    dsp(f'hl.dsp.focus({{ window = "address:{addr}" }})')


def focus_workspace(ws):
    dsp(f'hl.dsp.focus({{ workspace = "{ws}" }})')


def close_window(addr: str):
    focus_window(addr)
    dsp(f'hl.dsp.window.close({{ window = "address:{addr}" }})')


def kill_fullscreen_atlas_on_other_workspaces(target_ws):
    """Kill leftover fullscreen Atlas on *non-target* workspaces only.

    Never close Atlas already on the target workspace — just unset
    fullscreen/float so place() can tile it.
    """
    target = str(target_ws)
    killed = 0
    for c in clients():
        if not is_atlas_client(c):
            continue
        ws = c.get("workspace") or {}
        ws_id = str(ws.get("id") or "")
        ws_name = str(ws.get("name") or "")
        on_target = ws_id == target or ws_name == target
        addr = c.get("address")
        if not addr:
            continue
        fs = c.get("fullscreen") or 0
        try:
            fs_on = bool(int(fs))
        except Exception:
            fs_on = bool(fs)
        if on_target:
            if fs_on or c.get("floating"):
                log("unset fs/float on target Atlas", addr, "fs", fs)
                unset_float_fullscreen(addr)
            continue
        # Non-target leftover — close so it cannot cover the prior desktop
        log(
            "kill leftover Atlas",
            addr,
            "ws",
            ws_id,
            ws_name,
            "fs",
            fs,
            "float",
            c.get("floating"),
        )
        focus_window(addr)
        dsp("hl.dsp.window.fullscreen({ mode = 0 })")
        close_window(addr)
        killed += 1
        time.sleep(0.1)
    return killed


def unset_float_fullscreen(addr):
    """Disable fullscreen and floating before re-placing (windowrule recovery)."""
    focus_window(addr)
    # Live-proven: mode = 0 (not "off" / action unset)
    dsp(f'hl.dsp.window.fullscreen({{ mode = 0, window = "address:{addr}" }})')
    dsp("hl.dsp.window.fullscreen({ mode = 0 })")
    dsp(f'hl.dsp.window.float({{ action = "unset", window = "address:{addr}" }})')
    time.sleep(0.05)


def move_to_ws(addr, ws):
    # Absolute move-to-workspace via Lua (classic movetoworkspace fails on Omarchy 0.56)
    dsp(f'hl.dsp.window.move({{ workspace = "{ws}", window = "address:{addr}" }})')
    # Belt: focus then move without window key
    focus_window(addr)
    dsp(f'hl.dsp.window.move({{ workspace = "{ws}" }})')


def place(addr, x, y, w, h, name):
    """Absolute float + resize + move for 2x2 geometry (prefer over tiling)."""
    log(f"place {name} {addr} -> {x},{y} {w}x{h}")
    focus_window(addr)
    dsp(f'hl.dsp.window.fullscreen({{ mode = 0, window = "address:{addr}" }})')
    dsp("hl.dsp.window.fullscreen({ mode = 0 })")
    # Exact pixel grid needs floating
    dsp(f'hl.dsp.window.float({{ action = "set", window = "address:{addr}" }})')
    time.sleep(0.05)
    dsp(
        f'hl.dsp.window.resize({{ x = {int(w)}, y = {int(h)}, relative = false, '
        f'window = "address:{addr}" }})'
    )
    dsp(
        f'hl.dsp.window.move({{ x = {int(x)}, y = {int(y)}, relative = false, '
        f'window = "address:{addr}" }})'
    )
    # Re-assert after windowrules may re-fire
    dsp(f'hl.dsp.window.fullscreen({{ mode = 0, window = "address:{addr}" }})')


def top_bar_px(m):
    reserved = m.get("reserved") or [0, 0, 0, 0]
    try:
        # Hyprland reserved: [left, top, right, bottom] or similar
        top = int(reserved[1] if len(reserved) > 1 else 0)
    except Exception:
        top = 0
    if top <= 0:
        top = DEFAULT_TOP_BAR
    return top


def layout_rects(m):
    mx, my = int(m.get("x") or 0), int(m.get("y") or 0)
    W, H = int(m.get("width") or 1920), int(m.get("height") or 1080)
    bar = top_bar_px(m)
    y0 = my + bar
    usable_h = max(200, H - bar)
    half_w = W // 2
    half_h = usable_h // 2
    return {
        "atlas": (mx, y0, half_w, half_h),
        "nautilus": (mx + half_w, y0, W - half_w, half_h),
        "herdr": (mx, y0 + half_h, half_w, usable_h - half_h),
        "okstratr": (mx + half_w, y0 + half_h, W - half_w, usable_h - half_h),
    }, {"W": W, "H": H, "bar": bar, "mx": mx, "my": my}


def dump_geo(tag="GEO"):
    for c in clients():
        ws = c.get("workspace") or {}
        log(
            tag,
            c.get("class"),
            (c.get("title") or "")[:48],
            "ws",
            ws.get("id"),
            ws.get("name"),
            "at",
            c.get("at"),
            "size",
            c.get("size"),
            "float",
            c.get("floating"),
            "fs",
            c.get("fullscreen"),
        )


def main():
    ensure_hypr_env()

    # Optional: kill leftover fullscreen Atlas outside target before wait
    if os.environ.get("OKBAY_KILL_STALE_ATLAS", "1") == "1":
        kill_fullscreen_atlas_on_other_workspaces(WS)

    roles = wait_roles(timeout=float(os.environ.get("OKBAY_ARRANGE_WAIT") or "14"))
    log(
        "roles",
        {k: (v.get("address"), (v.get("title") or "")[:40], class_str(v)) for k, v in roles.items()},
    )
    missing = [r for r in ROLES if r not in roles]
    if missing:
        log("waiting still missing", missing)
        # One more wait slice
        roles = wait_roles(timeout=6.0)
        missing = [r for r in ROLES if r not in roles]
        if missing:
            log("MISSING_ROLES", missing)

    for _role, c in list(roles.items()):
        addr = c.get("address")
        if addr:
            unset_float_fullscreen(addr)
            move_to_ws(addr, WS)

    time.sleep(0.25)
    # Ensure target workspace focused (Lua — never bare workspace N)
    focus_workspace(WS)
    roles = wait_roles(timeout=4.0)
    m = mon()
    layout, meta = layout_rects(m)
    log("monitor", meta, "reserved", m.get("reserved"))

    for role, (x, y, w, h) in layout.items():
        c = roles.get(role)
        if not c or not c.get("address"):
            log("missing", role)
            continue
        place(c["address"], x, y, w, h, role)

    time.sleep(0.4)
    roles = wait_roles(timeout=3.0)
    for role, (x, y, w, h) in layout.items():
        c = roles.get(role)
        if not c or not c.get("address"):
            continue
        place(c["address"], x, y, w, h, role + "2")

    atlas = roles.get("atlas")
    if atlas and atlas.get("address"):
        # Final anti-fullscreen assert on Atlas + re-place TL
        addr = atlas["address"]
        focus_window(addr)
        dsp(f'hl.dsp.window.fullscreen({{ mode = 0, window = "address:{addr}" }})')
        dsp(f'hl.dsp.window.float({{ action = "set", window = "address:{addr}" }})')
        x, y, w, h = layout["atlas"]
        dsp(
            f'hl.dsp.window.resize({{ x = {int(w)}, y = {int(h)}, relative = false, '
            f'window = "address:{addr}" }})'
        )
        dsp(
            f'hl.dsp.window.move({{ x = {int(x)}, y = {int(y)}, relative = false, '
            f'window = "address:{addr}" }})'
        )
        focus_window(addr)

    log("ARRANGE_DONE")
    dump_geo("GEO")
    # Exit non-zero if still missing so the shell log notices
    if any(r not in roles for r in ROLES):
        sys.exit(2)


if __name__ == "__main__":
    main()
