#!/usr/bin/env python3
"""Place Atlas/Nautilus/Herdr/okstratr into a 2x2 grid on WS_TARGET.

Hardened for Omarchy Hyprland 0.56 Lua dispatchers (hl.dsp.*) — classic
`hyprctl dispatch workspace N` fails with: error: ')' expected.

Also hardened for OkbayAtlas windowrules (float+fullscreen) and Quickshell
FloatingWindow okstratr (title Okstratr / class quickshell|qs).

Hyprland 0.56 / Omarchy: mode=0 ENTERS fullscreen (fs→2);
mode="fullscreen" toggles OFF when fs!=0. Never clear with mode=0.

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
# Remeasure tolerance after ARRANGE_DONE: re-place if w/h off by >20%.
SIZE_TOLERANCE = float(os.environ.get("OKBAY_ARRANGE_SIZE_TOL") or "0.20")
# Live Omarchy: Herdr often collapses to ~163px; require ~half-pane (≥800 on typical).
HERDR_MIN_WIDTH = int(os.environ.get("OKBAY_HERDR_MIN_WIDTH") or "800")
CORRECT_PASSES = int(os.environ.get("OKBAY_ARRANGE_CORRECT_PASSES") or "3")


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
    # Dedicated profile ToS / pre-class: empty class, title hints Atlas launch.
    if not cls.strip() and not initial_cls.strip():
        tblob = f"{title} {initial}"
        if (
            "terms of service" in tblob
            or "additional terms" in tblob
            or "8766" in tblob
            or "atlas" in tblob
            or "127.0.0.1" in tblob
            or "okbay" in tblob
        ):
            return "atlas"

    # Nautilus
    if "nautilus" in b or "org.gnome.nautilus" in b:
        return "nautilus"

    # Herdr terminal — prefer app-id=herdr / title Herdr / initialTitle Herdr
    # (omarchy-launch-terminal-herdr often leaves class=foot title=omarchy: mac)
    if cls == "herdr" or initial_cls == "herdr":
        return "herdr"
    if title == "herdr" or initial == "herdr":
        return "herdr"
    if "herdr" in b:
        return "herdr"

    # okstratr — QML FloatingWindow (title Okstratr) under Quickshell
    # Match org.quickshell + Okstratr even when non-float (windowrules vary).
    if title == "okstratr" or initial == "okstratr":
        return "okstratr"
    if ("org.quickshell" in cls or "org.quickshell" in initial_cls or "quickshell" in cls) and (
        "okstratr" in title or "okstratr" in initial
    ):
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


def client_by_addr(addr: str):
    for c in clients():
        if c.get("address") == addr:
            return c
    return None


def fs_value(c) -> int:
    """Hyprland client.fullscreen: 0=off, nonzero=on (often 2)."""
    if not c:
        return 0
    fs = c.get("fullscreen") or 0
    try:
        return int(fs)
    except Exception:
        return 1 if fs else 0


def unset_fullscreen(addr: str) -> bool:
    """Clear fullscreen using Omarchy/Hyprland 0.56-safe toggle.

    LIVE PROVEN bug on Omarchy 0.56 Lua dispatchers:
      hl.dsp.window.fullscreen({ mode = 0 })  → ENTERS fullscreen (fs→2)
      hl.dsp.window.fullscreen({ mode = "fullscreen" }) → TOGGLES off when fs!=0
    Never call mode=0 to clear.
    """
    c = client_by_addr(addr)
    fs = fs_value(c)
    if fs == 0:
        return True
    log("unset_fullscreen toggle-off", addr, "fs", fs)
    focus_window(addr)
    # Toggle fullscreen OFF (string mode, not numeric 0)
    dsp(f'hl.dsp.window.fullscreen({{ mode = "fullscreen", window = "address:{addr}" }})')
    dsp('hl.dsp.window.fullscreen({ mode = "fullscreen" })')
    time.sleep(0.05)
    c2 = client_by_addr(addr)
    fs2 = fs_value(c2)
    if fs2 != 0:
        log("unset_fullscreen still on; toggle again", addr, "fs", fs2)
        focus_window(addr)
        dsp('hl.dsp.window.fullscreen({ mode = "fullscreen" })')
        time.sleep(0.05)
        fs2 = fs_value(client_by_addr(addr))
    return fs2 == 0


def unset_float_fullscreen(addr):
    """Disable fullscreen (toggle-off) and floating before re-placing."""
    focus_window(addr)
    unset_fullscreen(addr)
    dsp(f'hl.dsp.window.float({{ action = "unset", window = "address:{addr}" }})')
    time.sleep(0.05)


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
        fs = fs_value(c)
        if on_target:
            if fs or c.get("floating"):
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
        # Toggle off first if needed (never mode=0 — that ENTERS fullscreen)
        if fs:
            unset_fullscreen(addr)
        close_window(addr)
        killed += 1
        time.sleep(0.1)
    return killed


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
    # Ensure not fullscreen before resize/move (mode=0 ENTERS fs — never use it)
    if not unset_fullscreen(addr):
        log("place WARN still fullscreen before resize", name, addr)

    # Exact pixel grid needs floating
    dsp(f'hl.dsp.window.float({{ action = "set", window = "address:{addr}" }})')
    time.sleep(0.05)

    def do_resize_move():
        out_r = dsp(
            f'hl.dsp.window.resize({{ x = {int(w)}, y = {int(h)}, relative = false, '
            f'window = "address:{addr}" }})'
        )
        out_m = dsp(
            f'hl.dsp.window.move({{ x = {int(x)}, y = {int(y)}, relative = false, '
            f'window = "address:{addr}" }})'
        )
        return out_r, out_m

    out_r, out_m = do_resize_move()
    blob = f"{out_r} {out_m}".lower()
    if "window is fullscreen" in blob or fs_value(client_by_addr(addr)) != 0:
        log("place resize blocked by fullscreen; toggle+retry", name, addr)
        unset_fullscreen(addr)
        dsp(f'hl.dsp.window.float({{ action = "set", window = "address:{addr}" }})')
        time.sleep(0.05)
        do_resize_move()

    # Re-assert after windowrules may re-fire (toggle off only if still on)
    unset_fullscreen(addr)


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


def client_size(c):
    """Return (w, h) from hyprctl client size, or (0, 0)."""
    size = (c or {}).get("size") or [0, 0]
    try:
        return int(size[0] or 0), int(size[1] or 0)
    except Exception:
        return 0, 0


def size_off_target(actual_w, actual_h, target_w, target_h, tol=None):
    """True when width or height differs from target by more than tol (default 20%)."""
    if tol is None:
        tol = SIZE_TOLERANCE
    if target_w <= 0 or target_h <= 0:
        return True
    return (
        abs(actual_w - target_w) / float(target_w) > tol
        or abs(actual_h - target_h) / float(target_h) > tol
    )


def role_needs_correct(role, c, target, mon_meta=None):
    """Decide whether role geometry (or Herdr min-width / full-cover fs) needs re-place."""
    if not c:
        return True, "missing"
    _x, _y, w, h = target
    aw, ah = client_size(c)
    fs = fs_value(c)
    if fs != 0:
        # fs≥2 full-cover is the Omarchy overlay failure mode — always correct.
        mw = int((mon_meta or {}).get("W") or 0)
        mh = int((mon_meta or {}).get("H") or 0)
        if mw and mh and aw >= int(mw * 0.9) and ah >= int(mh * 0.9):
            return True, f"fs_full_cover fs={fs} {aw}x{ah}"
        return True, f"fs={fs} {aw}x{ah}"
    if size_off_target(aw, ah, w, h):
        return True, f"size {aw}x{ah} vs {w}x{h}"
    # Herdr must stay a usable BL half (≥~800 when target is that wide)
    if role == "herdr":
        min_w = min(HERDR_MIN_WIDTH, w) if w > 0 else HERDR_MIN_WIDTH
        if aw < min_w * 0.95:
            return True, f"herdr_narrow {aw}x{ah} min_w={min_w}"
    if not c.get("floating"):
        # Final 2x2 is float-based; tiled windows fight Hypr and collapse.
        return True, f"not_floating {aw}x{ah}"
    return False, f"ok {aw}x{ah}"


def ensure_float_set(addr: str):
    """Leave floating ON (final pass must not unset float)."""
    dsp(f'hl.dsp.window.float({{ action = "set", window = "address:{addr}" }})')


def place_final(addr, x, y, w, h, name):
    """Re-place for correction: toggle fs OFF if needed, SET float, resize/move; leave float on."""
    log(f"place_final {name} {addr} -> {x},{y} {w}x{h}")
    focus_window(addr)
    unset_fullscreen(addr)
    ensure_float_set(addr)
    time.sleep(0.05)
    dsp(
        f'hl.dsp.window.resize({{ x = {int(w)}, y = {int(h)}, relative = false, '
        f'window = "address:{addr}" }})'
    )
    dsp(
        f'hl.dsp.window.move({{ x = {int(x)}, y = {int(y)}, relative = false, '
        f'window = "address:{addr}" }})'
    )
    # Windowrules may re-fullscreen; toggle off only — never unset float on final pass
    if fs_value(client_by_addr(addr)) != 0:
        unset_fullscreen(addr)
        ensure_float_set(addr)
        time.sleep(0.05)
        dsp(
            f'hl.dsp.window.resize({{ x = {int(w)}, y = {int(h)}, relative = false, '
            f'window = "address:{addr}" }})'
        )
        dsp(
            f'hl.dsp.window.move({{ x = {int(x)}, y = {int(y)}, relative = false, '
            f'window = "address:{addr}" }})'
        )
    ensure_float_set(addr)


def correct_after_arrange(roles, layout, meta):
    """After ARRANGE_DONE: remeasure; re-place any role off by >20% (or Herdr <~800).

    Leaves floats set. Clears fs full-cover. Up to CORRECT_PASSES rounds.
    """
    for i in range(max(1, CORRECT_PASSES)):
        roles = wait_roles(timeout=2.5) or roles
        bad = []
        for role, rect in layout.items():
            c = roles.get(role)
            needs, why = role_needs_correct(role, c, rect, meta)
            log("MEASURE", role, why, "float", (c or {}).get("floating"), "fs", fs_value(c))
            if needs and c and c.get("address"):
                bad.append((role, c, rect, why))
            elif needs:
                log("CORRECT skip missing", role, why)
        if not bad:
            log("CORRECT_OK pass", i)
            return roles
        for role, c, rect, why in bad:
            x, y, w, h = rect
            log("CORRECT", role, why, "->", f"{w}x{h}")
            place_final(c["address"], x, y, w, h, f"{role}_correct{i}")
        time.sleep(0.35)
    # Last measure for GEO / exit status
    roles = wait_roles(timeout=2.0) or roles
    still = []
    for role, rect in layout.items():
        c = roles.get(role)
        needs, why = role_needs_correct(role, c, rect, meta)
        if needs:
            still.append((role, why))
            # One last final place attempt
            if c and c.get("address"):
                x, y, w, h = rect
                place_final(c["address"], x, y, w, h, f"{role}_correct_last")
                ensure_float_set(c["address"])
                unset_fullscreen(c["address"])
    if still:
        log("CORRECT_STILL_OFF", still)
    else:
        log("CORRECT_OK pass", "last")
    return wait_roles(timeout=1.5) or roles


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

    roles = wait_roles(timeout=float(os.environ.get("OKBAY_ARRANGE_WAIT") or "22"))
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
        x, y, w, h = layout["atlas"]
        place(addr, x, y, w, h, "atlas_final")
        focus_window(addr)

    log("ARRANGE_DONE")
    # Hypr fights floats: Herdr often collapses (~163px); Atlas TL not stable.
    # Remeasure and re-place any role whose w/h is off by >20%; leave floats set.
    roles = correct_after_arrange(roles, layout, meta)
    dump_geo("GEO")
    # Fail if roles missing or Herdr still absurdly narrow / any fs full-cover
    fail = False
    if any(r not in roles for r in ROLES):
        log("MISSING_ROLES_FINAL", [r for r in ROLES if r not in roles])
        fail = True
    for role, rect in layout.items():
        c = roles.get(role)
        needs, why = role_needs_correct(role, c, rect, meta)
        if needs:
            log("FINAL_OFF", role, why)
            # Still exit 0 for transient Hypr races unless missing/full-cover/herdr collapsed
            if role == "herdr" or (c and fs_value(c) != 0):
                fail = True
    if fail:
        sys.exit(2)


if __name__ == "__main__":
    main()
