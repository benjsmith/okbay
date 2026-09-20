#!/usr/bin/env python3
"""Place Atlas/Nautilus/Herdr/okstratr into a 2x2 grid on WS_TARGET.

Hardened for Omarchy Hyprland 0.56 Lua dispatchers (hl.dsp.*) — classic
`hyprctl dispatch workspace N` fails with: error: ')' expected.

Also hardened for OkbayAtlas windowrules (float+fullscreen) and Quickshell
FloatingWindow okstratr (title Okstratr / class quickshell|qs).

Hyprland 0.56 / Omarchy: mode=0 ENTERS fullscreen (fs→2);
mode="fullscreen" toggles OFF when fs!=0. Never clear with mode=0.

LIVE PROVEN (Omarchy 0.56 Mac Mini): NEVER float-unset before/during arrange —
float-unset when moving onto the WS dumps panes into dwindle columns (tall skinny
tiled sizes); later place_final then races Hypr. Recipe that sticks quadrants:
  1) Close ALL non-floating Nautilus on the target workspace first.
  2) For each role: float set → sleep ~150ms → resize absolute → move absolute →
     move absolute again (hl.dsp.window.*).
  3) Two full rounds over atlas/nautilus/herdr/okstratr with ~400ms settle.
After ARRANGE_DONE: correct_after_arrange still remeasures pos (~40px) / size
(~20%), re-floats if tiled, pins, and force-places from stored addresses.

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
# Position tolerance after ARRANGE_DONE: re-place if x/y off by >40px (Hypr recenters floats).
POS_TOLERANCE = int(os.environ.get("OKBAY_ARRANGE_POS_TOL") or "40")
# Live-proven round order: TL→TR→BL→BR (atlas/nautilus/herdr/okstratr).
PLACE_ORDER = ("atlas", "nautilus", "herdr", "okstratr")
SETTLE_SEC = float(os.environ.get("OKBAY_ARRANGE_SETTLE") or "0.40")
# After float set, wait before resize/move so Hypr commits floating (Omarchy 0.56).
FLOAT_SETTLE_SEC = float(os.environ.get("OKBAY_ARRANGE_FLOAT_SETTLE") or "0.15")


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
    """Disable fullscreen only — NEVER float-unset (dumps into dwindle on Omarchy 0.56).

    Kept name for callers; float is asserted SET so move_to_ws keeps floating geom.
    """
    focus_window(addr)
    unset_fullscreen(addr)
    # Critical: do not float-unset. Set float so later absolute place sticks.
    dsp(f'hl.dsp.window.float({{ action = "set", window = "address:{addr}" }})')
    time.sleep(FLOAT_SETTLE_SEC)


def kill_fullscreen_atlas_on_other_workspaces(target_ws):
    """Kill leftover fullscreen Atlas on *non-target* workspaces only.

    Never close Atlas already on the target workspace — clear fullscreen only
    and ensure float stays set (never float-unset).
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
            # Only clear fullscreen; keep/ensure float (never float-unset).
            if fs:
                log("unset fs on target Atlas (keep float)", addr, "fs", fs)
                unset_fullscreen(addr)
            ensure_float_set(addr)
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
    """Live recipe: float set → ~150ms → resize abs → move abs → move abs again."""
    log(f"place {name} {addr} -> {x},{y} {w}x{h}")
    focus_window(addr)
    # Ensure not fullscreen before resize/move (mode=0 ENTERS fs — never use it)
    if not unset_fullscreen(addr):
        log("place WARN still fullscreen before resize", name, addr)

    # Exact pixel grid needs floating — NEVER float-unset before/during place.
    dsp(f'hl.dsp.window.float({{ action = "set", window = "address:{addr}" }})')
    time.sleep(FLOAT_SETTLE_SEC)

    def do_resize_move():
        out_r = dsp(
            f'hl.dsp.window.resize({{ x = {int(w)}, y = {int(h)}, relative = false, '
            f'window = "address:{addr}" }})'
        )
        out_m = dsp(
            f'hl.dsp.window.move({{ x = {int(x)}, y = {int(y)}, relative = false, '
            f'window = "address:{addr}" }})'
        )
        # Second absolute move fights Omarchy float-center (y≈378 on 1440)
        time.sleep(0.04)
        out_m2 = dsp(
            f'hl.dsp.window.move({{ x = {int(x)}, y = {int(y)}, relative = false, '
            f'window = "address:{addr}" }})'
        )
        return out_r, f"{out_m} {out_m2}"

    # If still tiled after settle, re-float then wait again before geom
    c0 = client_by_addr(addr)
    if not (c0 and c0.get("floating")):
        dsp(f'hl.dsp.window.float({{ action = "set", window = "address:{addr}" }})')
        time.sleep(FLOAT_SETTLE_SEC)

    out_r, out_m = do_resize_move()
    blob = f"{out_r} {out_m}".lower()
    if "window is fullscreen" in blob or fs_value(client_by_addr(addr)) != 0:
        log("place resize blocked by fullscreen; toggle+retry", name, addr)
        unset_fullscreen(addr)
        dsp(f'hl.dsp.window.float({{ action = "set", window = "address:{addr}" }})')
        time.sleep(FLOAT_SETTLE_SEC)
        do_resize_move()

    # Re-assert after windowrules may re-fire (toggle off only if still on)
    unset_fullscreen(addr)
    # Leave floating ON for 2x2 (do not unset)
    dsp(f'hl.dsp.window.float({{ action = "set", window = "address:{addr}" }})')


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


def client_at(c):
    """Return (x, y) from hyprctl client at, or (0, 0)."""
    at = (c or {}).get("at") or [0, 0]
    try:
        return int(at[0] or 0), int(at[1] or 0)
    except Exception:
        return 0, 0


def pos_off_target(actual_x, actual_y, target_x, target_y, tol=None):
    """True when x or y differs from target by more than tol px (default 40)."""
    if tol is None:
        tol = POS_TOLERANCE
    return abs(actual_x - target_x) > tol or abs(actual_y - target_y) > tol


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
    """Decide whether role geometry needs re-place (pos, size, float, fs, Herdr width)."""
    if not c:
        return True, "missing"
    tx, ty, w, h = target
    aw, ah = client_size(c)
    ax, ay = client_at(c)
    fs = fs_value(c)
    if fs != 0:
        # fs≥2 full-cover is the Omarchy overlay failure mode — always correct.
        mw = int((mon_meta or {}).get("W") or 0)
        mh = int((mon_meta or {}).get("H") or 0)
        if mw and mh and aw >= int(mw * 0.9) and ah >= int(mh * 0.9):
            return True, f"fs_full_cover fs={fs} {aw}x{ah}"
        return True, f"fs={fs} {aw}x{ah}"
    if not c.get("floating"):
        # Final 2x2 is float-based; tiled windows fight Hypr and collapse / recenter.
        return True, f"not_floating at={ax},{ay} {aw}x{ah}"
    if pos_off_target(ax, ay, tx, ty):
        return True, f"pos {ax},{ay} vs {tx},{ty}"
    if size_off_target(aw, ah, w, h):
        return True, f"size {aw}x{ah} vs {w}x{h}"
    # Herdr must stay a usable BL half (≥~800 when target is that wide)
    if role == "herdr":
        min_w = min(HERDR_MIN_WIDTH, w) if w > 0 else HERDR_MIN_WIDTH
        if aw < min_w * 0.95:
            return True, f"herdr_narrow {aw}x{ah} min_w={min_w}"
    return False, f"ok at={ax},{ay} {aw}x{ah}"


def ensure_float_set(addr: str):
    """Leave floating ON (final pass must not unset float)."""
    dsp(f'hl.dsp.window.float({{ action = "set", window = "address:{addr}" }})')


def pin_window(addr: str, on: bool = True):
    """Pin floating window so Hypr tiling/recenter cannot steal it (Omarchy Lua)."""
    action = "set" if on else "unset"
    out = dsp(f'hl.dsp.window.pin({{ action = "{action}", window = "address:{addr}" }})')
    blob = (out or "").lower()
    if "error" in blob or "expected" in blob or "unknown" in blob:
        # Toggle form / no action key (some Omarchy builds)
        dsp(f'hl.dsp.window.pin({{ window = "address:{addr}" }})')


def ensure_floating_geom(addr: str, name: str) -> bool:
    """Re-set float if Hypr tiled us; return True when floating after assert."""
    c = client_by_addr(addr)
    if c and c.get("floating"):
        return True
    log("re-float before geom", name, addr, "was_float", (c or {}).get("floating"))
    ensure_float_set(addr)
    time.sleep(FLOAT_SETTLE_SEC)
    c2 = client_by_addr(addr)
    if not (c2 and c2.get("floating")):
        # Focus then float again — address-only set sometimes no-ops when tiled
        focus_window(addr)
        ensure_float_set(addr)
        time.sleep(FLOAT_SETTLE_SEC)
        c2 = client_by_addr(addr)
    return bool(c2 and c2.get("floating"))


def _resize_move(addr, x, y, w, h):
    dsp(
        f'hl.dsp.window.resize({{ x = {int(w)}, y = {int(h)}, relative = false, '
        f'window = "address:{addr}" }})'
    )
    dsp(
        f'hl.dsp.window.move({{ x = {int(x)}, y = {int(y)}, relative = false, '
        f'window = "address:{addr}" }})'
    )
    # Second move sticks against Hypr float-center (~(W-w)/2+bar → y≈378 on 1440)
    time.sleep(0.04)
    dsp(
        f'hl.dsp.window.move({{ x = {int(x)}, y = {int(y)}, relative = false, '
        f'window = "address:{addr}" }})'
    )


def place_final(addr, x, y, w, h, name, do_pin: bool = True):
    """Re-place for correction: fs OFF, float SET (+remeasure), resize/move, optional pin."""
    log(f"place_final {name} {addr} -> {x},{y} {w}x{h}")
    # Prefer address-scoped ops; focus only when fs must toggle
    if fs_value(client_by_addr(addr)) != 0:
        focus_window(addr)
        unset_fullscreen(addr)
    if not ensure_floating_geom(addr, name):
        focus_window(addr)
        ensure_float_set(addr)
        time.sleep(FLOAT_SETTLE_SEC)
    _resize_move(addr, x, y, w, h)
    # Windowrules may re-fullscreen or retile mid-move
    c = client_by_addr(addr)
    if fs_value(c) != 0 or not (c and c.get("floating")):
        log("place_final retry after fs/tile fight", name, addr)
        if fs_value(c) != 0:
            focus_window(addr)
            unset_fullscreen(addr)
        ensure_floating_geom(addr, name)
        _resize_move(addr, x, y, w, h)
    ensure_float_set(addr)
    if do_pin:
        pin_window(addr, True)
    # Remeasure: if still not floating or pos/size way off, one more geom pass
    time.sleep(0.06)
    c = client_by_addr(addr)
    if c:
        aw, ah = client_size(c)
        ax, ay = client_at(c)
        if (not c.get("floating")) or pos_off_target(ax, ay, x, y) or size_off_target(aw, ah, w, h):
            log(
                "place_final post-check still off",
                name,
                f"at={ax},{ay}",
                f"{aw}x{ah}",
                "float",
                c.get("floating"),
            )
            ensure_floating_geom(addr, name)
            _resize_move(addr, x, y, w, h)
            ensure_float_set(addr)
            if do_pin:
                pin_window(addr, True)


def temp_float_rules_for_addrs(addrs):
    """Optional temporary float force via windowrulev2 on exact addresses during arrange."""
    if os.environ.get("OKBAY_ARRANGE_TEMP_RULES", "1") != "1":
        return
    for addr in addrs:
        if not addr:
            continue
        # keyword appends; address-scoped so we do not blanket-class float forever
        run(["hyprctl", "keyword", "windowrulev2", f"float,address:{addr}"])
        log("TEMP_RULE float", addr)


def role_score(c, target_ws: str, prefer_float: bool = True):
    """Higher is better when choosing among duplicate role clients (extra Nautilus)."""
    ws = c.get("workspace") or {}
    ws_id = str(ws.get("id") or "")
    ws_name = str(ws.get("name") or "")
    on_target = 1 if (ws_id == str(target_ws) or ws_name == str(target_ws)) else 0
    floating = 1 if c.get("floating") else 0
    if not prefer_float:
        floating = 0
    size = c.get("size") or [0, 0]
    try:
        area = int(size[0] or 0) * int(size[1] or 0)
    except Exception:
        area = 0
    # Prefer not fullscreen
    fs_ok = 1 if fs_value(c) == 0 else 0
    return (on_target, floating, fs_ok, area, -(c.get("focusHistoryID") or 0))


def collect_role_candidates():
    """Map role -> list of matching clients (okstratr_maybe folded into okstratr)."""
    found = {r: [] for r in ROLES}
    maybes = []
    for c in clients():
        role = classify(c)
        if role == "okstratr_maybe":
            maybes.append(c)
            continue
        if role in found:
            found[role].append(c)
    if maybes and not found["okstratr"]:
        found["okstratr"] = maybes
    elif maybes:
        found["okstratr"].extend(maybes)
    return found


def select_roles(target_ws: str, timeout: float = 14.0):
    """Wait until all roles seen; pick best candidate per role (target WS + floating)."""
    deadline = time.time() + timeout
    best = {}
    while time.time() < deadline:
        cands = collect_role_candidates()
        chosen = {}
        for role in ROLES:
            lst = cands.get(role) or []
            if not lst:
                continue
            lst.sort(key=lambda c: role_score(c, target_ws), reverse=True)
            chosen[role] = lst[0]
        best = chosen
        if all(k in chosen for k in ROLES):
            return chosen
        time.sleep(0.25)
    return best


def close_tiled_nautilus_on_ws(target_ws: str, keep_addr: str | None = None):
    """Close ALL non-floating Nautilus on target WS (live-proven step 1).

    Tiled Nautilus on the product workspace dumps peers into dwindle columns.
    Optionally keep one address (chosen TR pane) — it will be float-set next.
    """
    closed = 0
    for c in clients():
        if classify(c) != "nautilus":
            continue
        if c.get("floating"):
            continue
        addr = c.get("address")
        if not addr or (keep_addr and addr == keep_addr):
            continue
        ws = c.get("workspace") or {}
        ws_id = str(ws.get("id") or "")
        ws_name = str(ws.get("name") or "")
        on_target = ws_id == str(target_ws) or ws_name == str(target_ws)
        if not on_target:
            continue
        log("close tiled nautilus on target", addr, "ws", ws_id, ws_name)
        close_window(addr)
        closed += 1
        time.sleep(0.08)
    return closed


def close_extra_windows(chosen: dict, target_ws: str):
    """Close duplicate Nautilus (and non-chosen Atlas) fighting the float 2x2 on target WS.

    Never close the four chosen addresses. Extra tiled Nautilus full-width was
    live-proven to retile Atlas/okstratr off their quadrants.
    """
    keep = {c.get("address") for c in chosen.values() if c and c.get("address")}
    closed = 0
    for c in clients():
        addr = c.get("address")
        if not addr or addr in keep:
            continue
        role = classify(c)
        if role == "okstratr_maybe":
            role = "okstratr"
        ws = c.get("workspace") or {}
        ws_id = str(ws.get("id") or "")
        ws_name = str(ws.get("name") or "")
        on_target = ws_id == str(target_ws) or ws_name == str(target_ws)
        # Always drop extra Nautilus (any WS) — duplicates fight tiling
        if role == "nautilus":
            log("close extra nautilus", addr, "ws", ws_id, ws_name, "float", c.get("floating"))
            close_window(addr)
            closed += 1
            time.sleep(0.08)
            continue
        # Extra Atlas on target WS only (leftover on other WS handled elsewhere)
        if role == "atlas" and on_target:
            log("close extra atlas on target", addr)
            if fs_value(c):
                unset_fullscreen(addr)
            close_window(addr)
            closed += 1
            time.sleep(0.08)
    return closed


def force_place_all(addrs: dict, layout: dict, tag: str):
    """Force-place all four roles from stored addresses (ignore reclassify races)."""
    for role in PLACE_ORDER:
        addr = addrs.get(role)
        rect = layout.get(role)
        if not addr or not rect:
            log("force_place skip", role, tag)
            continue
        x, y, w, h = rect
        place_final(addr, x, y, w, h, f"{role}_{tag}", do_pin=True)
        time.sleep(0.05)


def roles_from_addrs(addrs: dict):
    """Rebuild roles dict from stored addresses (stable across Hypr retile)."""
    out = {}
    for role, addr in addrs.items():
        c = client_by_addr(addr)
        if c:
            out[role] = c
    return out


def correct_after_arrange(roles, layout, meta, addrs=None):
    """After ARRANGE_DONE: remeasure pos+size; re-place; settle; force-place all four.

    Leaves floats set + pinned. Clears fs full-cover. Up to CORRECT_PASSES rounds
    then one settle force-place from stored addresses.
    """
    if addrs is None:
        addrs = {r: (roles.get(r) or {}).get("address") for r in ROLES}
        addrs = {r: a for r, a in addrs.items() if a}

    for i in range(max(1, CORRECT_PASSES)):
        # Prefer address-stable clients over reclassify (extra Nautilus races)
        fresh = roles_from_addrs(addrs)
        if len(fresh) < len(addrs):
            # Fill any missing via select
            selected = select_roles(WS, timeout=2.0)
            for role, c in selected.items():
                if role not in fresh and c.get("address"):
                    fresh[role] = c
                    addrs[role] = c["address"]
        roles = fresh or roles
        bad = []
        for role in PLACE_ORDER:
            rect = layout.get(role)
            if not rect:
                continue
            c = roles.get(role)
            needs, why = role_needs_correct(role, c, rect, meta)
            ax, ay = client_at(c)
            log(
                "MEASURE",
                role,
                why,
                "at",
                f"{ax},{ay}",
                "float",
                (c or {}).get("floating"),
                "fs",
                fs_value(c),
            )
            if needs and c and c.get("address"):
                bad.append((role, c, rect, why))
                addrs[role] = c["address"]
            elif needs:
                log("CORRECT skip missing", role, why)
        if not bad:
            log("CORRECT_OK pass", i)
            break
        for role, c, rect, why in bad:
            x, y, w, h = rect
            log("CORRECT", role, why, "->", f"{x},{y} {w}x{h}")
            place_final(c["address"], x, y, w, h, f"{role}_correct{i}")
        time.sleep(SETTLE_SEC)

    # Settle then force-place ALL four from stored addresses (sticks quadrants)
    log("CORRECT_SETTLE force-place all", list(addrs.keys()))
    time.sleep(SETTLE_SEC)
    force_place_all(addrs, layout, "settle")
    time.sleep(SETTLE_SEC)
    force_place_all(addrs, layout, "settle2")
    time.sleep(0.25)

    roles = roles_from_addrs(addrs) or select_roles(WS, timeout=1.5) or roles
    still = []
    for role in PLACE_ORDER:
        rect = layout.get(role)
        if not rect:
            continue
        c = roles.get(role)
        needs, why = role_needs_correct(role, c, rect, meta)
        if needs:
            still.append((role, why))
            addr = (c or {}).get("address") or addrs.get(role)
            if addr:
                x, y, w, h = rect
                place_final(addr, x, y, w, h, f"{role}_correct_last")
                ensure_float_set(addr)
                if fs_value(client_by_addr(addr)) != 0:
                    unset_fullscreen(addr)
    if still:
        # One more micro-settle measure
        time.sleep(0.2)
        roles = roles_from_addrs(addrs) or roles
        still2 = []
        for role in PLACE_ORDER:
            rect = layout.get(role)
            c = roles.get(role)
            needs, why = role_needs_correct(role, c, rect, meta)
            if needs:
                still2.append((role, why))
        if still2:
            log("CORRECT_STILL_OFF", still2)
        else:
            log("CORRECT_OK pass", "last")
    else:
        log("CORRECT_OK pass", "last")
    return roles_from_addrs(addrs) or select_roles(WS, timeout=1.0) or roles


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

    # Step 1 (live-proven): close ALL non-floating Nautilus on target WS first
    tiled_n = close_tiled_nautilus_on_ws(WS)
    if tiled_n:
        log("closed_tiled_nautilus_pre", tiled_n)
        time.sleep(0.15)

    wait_s = float(os.environ.get("OKBAY_ARRANGE_WAIT") or "22")
    roles = select_roles(WS, timeout=wait_s)
    if len(roles) < len(ROLES):
        # Fallback to legacy wait_roles classify
        legacy = wait_roles(timeout=2.0)
        for k, v in legacy.items():
            roles.setdefault(k, v)
    log(
        "roles",
        {k: (v.get("address"), (v.get("title") or "")[:40], class_str(v)) for k, v in roles.items()},
    )
    missing = [r for r in ROLES if r not in roles]
    if missing:
        log("waiting still missing", missing)
        roles = select_roles(WS, timeout=6.0) or roles
        missing = [r for r in ROLES if r not in roles]
        if missing:
            log("MISSING_ROLES", missing)

    # Drop duplicate Nautilus / extra Atlas before move — tiled extras retile floats
    keep_nau = (roles.get("nautilus") or {}).get("address")
    tiled_n2 = close_tiled_nautilus_on_ws(WS, keep_addr=keep_nau)
    if tiled_n2:
        log("closed_tiled_nautilus_pre_move", tiled_n2)
    closed = close_extra_windows(roles, WS)
    log("closed_extras", closed)
    if closed or tiled_n2:
        time.sleep(0.15)
        # Re-bind chosen after closes
        roles = select_roles(WS, timeout=3.0) or roles

    addrs = {}
    for role in ROLES:
        c = roles.get(role)
        addr = (c or {}).get("address")
        if addr:
            addrs[role] = addr
            # Initial: clear fs; do NOT leave tiled — set float early so move keeps float
            focus_window(addr)
            unset_fullscreen(addr)
            ensure_float_set(addr)
            move_to_ws(addr, WS)

    time.sleep(0.25)
    # Ensure target workspace focused (Lua — never bare workspace N)
    focus_workspace(WS)
    # Close extras again after move (Nautilus sometimes remaps on WS switch)
    roles = roles_from_addrs(addrs) or select_roles(WS, timeout=4.0) or roles
    for role, c in list(roles.items()):
        if c.get("address"):
            addrs[role] = c["address"]
    closed2 = close_extra_windows(roles, WS)
    if closed2:
        log("closed_extras_after_move", closed2)
        time.sleep(0.1)
        roles = roles_from_addrs(addrs) or select_roles(WS, timeout=2.0) or roles

    m = mon()
    layout, meta = layout_rects(m)
    log("monitor", meta, "reserved", m.get("reserved"))

    temp_float_rules_for_addrs(list(addrs.values()))

    # First place pass — PLACE_ORDER avoids focus stealing into tile mid-grid
    for role in PLACE_ORDER:
        rect = layout.get(role)
        c = roles.get(role)
        if not rect or not c or not c.get("address"):
            log("missing", role)
            continue
        x, y, w, h = rect
        place(c["address"], x, y, w, h, role)
        ensure_float_set(c["address"])
        pin_window(c["address"], True)

    time.sleep(SETTLE_SEC)
    roles = roles_from_addrs(addrs) or select_roles(WS, timeout=3.0) or roles
    for role in PLACE_ORDER:
        rect = layout.get(role)
        c = roles.get(role)
        if not rect or not c or not c.get("address"):
            continue
        x, y, w, h = rect
        addrs[role] = c["address"]
        place(c["address"], x, y, w, h, role + "2")
        ensure_float_set(c["address"])
        pin_window(c["address"], True)

    atlas_addr = addrs.get("atlas")
    if atlas_addr and "atlas" in layout:
        # Final anti-fullscreen assert on Atlas + re-place TL via place_final
        x, y, w, h = layout["atlas"]
        place_final(atlas_addr, x, y, w, h, "atlas_final")

    log("ARRANGE_DONE")
    # Hypr fights floats: recenters to ~1718,378; tiling drops float; extras retile.
    # Remeasure pos+size; settle force-place all four from stored addresses.
    roles = correct_after_arrange(roles, layout, meta, addrs=addrs)
    dump_geo("GEO")
    # Fail if roles missing or Herdr still absurdly narrow / any fs full-cover / pos off
    fail = False
    if any(r not in roles for r in ROLES):
        log("MISSING_ROLES_FINAL", [r for r in ROLES if r not in roles])
        fail = True
    for role in PLACE_ORDER:
        rect = layout.get(role)
        if not rect:
            continue
        c = roles.get(role)
        needs, why = role_needs_correct(role, c, rect, meta)
        if needs:
            log("FINAL_OFF", role, why)
            # Exit 2 on herdr / fullscreen / position-off / not-floating (quadrant stick)
            if role == "herdr" or (c and fs_value(c) != 0):
                fail = True
            elif why.startswith("pos ") or why.startswith("not_floating"):
                fail = True
    if fail:
        sys.exit(2)


if __name__ == "__main__":
    main()
