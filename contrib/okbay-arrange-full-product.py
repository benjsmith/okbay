#!/usr/bin/env python3
"""Minimal Omarchy 0.56 2x2 arrange — proven recipe.

NEVER float action=set (tiles floating windows). Toggle only when tiled.
"""
from __future__ import annotations
import json, os, subprocess, sys, time

LOG = os.environ.get("OKBAY_FULL_PRODUCT_LOG", "/tmp/okbay-full-product.log")
WS = int(os.environ.get("OKBAY_FULL_PRODUCT_WS", "12") or 12)

def log(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def hypr(*args):
    return subprocess.run(["hyprctl", *args], capture_output=True, text=True)

def dsp(lua: str) -> None:
    r = hypr("dispatch", lua)
    out = (r.stdout or r.stderr or "").strip()
    log("DSP", lua[:100], "->", out[:80])

def clients():
    return json.loads(hypr("clients", "-j").stdout or "[]")

def role_of(c):
    b = " ".join(str(c.get(k) or "") for k in ("class", "initialClass", "title", "initialTitle")).lower()
    cls = str(c.get("class") or "").lower()
    if "okbayatlas" in b or (cls.startswith("chrome-") and ("atlas" in b or "8766" in b or "127.0.0.1" in b)):
        return "atlas"
    if "nautilus" in b:
        return "nautilus"
    if cls == "herdr" or "herdr" == str(c.get("title") or "").lower():
        return "herdr"
    if "okstratr" in str(c.get("title") or "").lower():
        return "okstratr"
    return None

def pick_roles(ws: int):
    by = {}
    for c in clients():
        r = role_of(c)
        if not r:
            continue
        wid = int((c.get("workspace") or {}).get("id") or 0)
        sc = (
            1 if wid == ws else 0,
            1 if c.get("floating") else 0,
            -abs((c.get("size") or [0, 0])[0] - 1720),
        )
        if r not in by or sc > by[r][0]:
            by[r] = (sc, c)
    return {r: t[1] for r, t in by.items()}

def ensure_float(addr: str) -> None:
    for c in clients():
        if c.get("address") == addr:
            if c.get("floating"):
                return
            log("ensure_float toggle", addr)
            dsp(f'hl.dsp.window.float({{ action = "toggle", window = "address:{addr}" }})')
            time.sleep(0.15)
            return

def place(addr: str, x: int, y: int, w: int, h: int, name: str) -> None:
    log("place", name, addr, "->", f"{x},{y}", f"{w}x{h}")
    dsp(f'hl.dsp.focus({{ window = "address:{addr}" }})')
    ensure_float(addr)
    time.sleep(0.05)
    dsp(f'hl.dsp.window.resize({{ x = {w}, y = {h}, relative = false, window = "address:{addr}" }})')
    dsp(f'hl.dsp.window.move({{ x = {x}, y = {y}, relative = false, window = "address:{addr}" }})')
    time.sleep(0.05)
    dsp(f'hl.dsp.window.move({{ x = {x}, y = {y}, relative = false, window = "address:{addr}" }})')

def close_tiled_nautilus_except(ws: int, keep: set[str]) -> None:
    n = 0
    for c in clients():
        wid = int((c.get("workspace") or {}).get("id") or 0)
        if wid != ws:
            continue
        if "nautilus" not in str(c.get("class") or "").lower():
            continue
        addr = c.get("address")
        if addr in keep:
            continue
        if c.get("floating"):
            continue
        log("close tiled nautilus", addr)
        dsp(f'hl.dsp.window.close({{ window = "address:{addr}" }})')
        n += 1
    if n:
        time.sleep(0.3)
        log("closed_tiled_nautilus_pre", n)

def mon_geom():
    mons = json.loads(hypr("monitors", "-j").stdout or "[]")
    m = mons[0] if mons else {"width": 3440, "height": 1440, "reserved": [0, 24, 0, 0]}
    W = int(m.get("width") or 3440)
    H = int(m.get("height") or 1440)
    reserved = m.get("reserved") or [0, 24, 0, 0]
    bar = int(reserved[1] or 24)
    tw, th = W // 2, (H - bar) // 2
    return W, H, bar, tw, th

def main():
    global WS
    raw = os.environ.get("OKBAY_FULL_PRODUCT_WS", str(WS))
    if raw.isdigit():
        WS = int(raw)
    W, H, bar, tw, th = mon_geom()
    layout = {
        "atlas": (0, bar, tw, th),
        "nautilus": (tw, bar, tw, th),
        "herdr": (0, bar + th, tw, th),
        "okstratr": (tw, bar + th, tw, th),
    }
    log("monitor", {"W": W, "H": H, "bar": bar, "tw": tw, "th": th}, "ws", WS)
    dsp(f'hl.dsp.focus({{ workspace = "{WS}" }})')

    roles = pick_roles(WS)
    if len(roles) < 4:
        by = {}
        for c in clients():
            r = role_of(c)
            if not r:
                continue
            sc = (1 if c.get("floating") else 0,)
            if r not in by or sc > by[r][0]:
                by[r] = (sc, c)
        roles = {r: t[1] for r, t in by.items()}

    keep = {c["address"] for c in roles.values()}
    close_tiled_nautilus_except(WS, keep)
    log("roles", {r: (c.get("address"), c.get("title"), c.get("class")) for r, c in roles.items()})

    for r, c in list(roles.items()):
        addr = c["address"]
        wid = int((c.get("workspace") or {}).get("id") or 0)
        if wid != WS:
            dsp(f'hl.dsp.focus({{ window = "address:{addr}" }})')
            dsp(f'hl.dsp.window.move({{ workspace = "{WS}", window = "address:{addr}" }})')
            time.sleep(0.1)
    time.sleep(0.2)
    by = {}
    for c in clients():
        if int((c.get("workspace") or {}).get("id") or 0) != WS:
            continue
        r = role_of(c)
        if r:
            by[r] = c
    if by:
        roles = by
    log("roles_on_ws", list(roles))

    order = ["atlas", "nautilus", "herdr", "okstratr"]
    for round_i in range(2):
        for r in order:
            c = roles.get(r)
            if not c:
                log("missing", r)
                continue
            x, y, w, h = layout[r]
            place(c["address"], x, y, w, h, f"{r}{round_i}")
        time.sleep(0.4)
        by = {}
        for c in clients():
            if int((c.get("workspace") or {}).get("id") or 0) != WS:
                continue
            rr = role_of(c)
            if rr:
                by[rr] = c
        roles.update(by)

    log("ARRANGE_DONE")
    ok = True
    for r, (x, y, w, h) in layout.items():
        c = roles.get(r)
        if not c:
            log("FINAL_OFF", r, "missing")
            ok = False
            continue
        cur = None
        for cc in clients():
            if cc.get("address") == c["address"]:
                cur = cc
                break
        if not cur:
            log("FINAL_OFF", r, "gone")
            ok = False
            continue
        at = cur.get("at") or [0, 0]
        sz = cur.get("size") or [0, 0]
        fl = bool(cur.get("floating"))
        fs = int(cur.get("fullscreen") or 0)
        pos = abs(int(at[0]) - x) <= 40 and abs(int(at[1]) - y) <= 40
        size = abs(int(sz[0]) - w) / max(w, 1) <= 0.2 and abs(int(sz[1]) - h) / max(h, 1) <= 0.2
        log("MEASURE", r, "at", at, "size", sz, "float", fl, "fs", fs,
            "POS_OK" if pos else "POS_BAD", "SIZE_OK" if size else "SIZE_BAD")
        if not (pos and size and fl and fs == 0):
            ok = False
            place(c["address"], x, y, w, h, f"{r}_fix")
    if ok:
        log("CORRECT_OK")
        log("SMOKE_GREEN_QUADRANTS")
    else:
        time.sleep(0.3)
        ok2 = True
        for r, (x, y, w, h) in layout.items():
            found = None
            for c in clients():
                if int((c.get("workspace") or {}).get("id") or 0) != WS:
                    continue
                if role_of(c) == r:
                    found = c
                    break
            if not found:
                log("FINAL_OFF", r, "missing")
                ok2 = False
                continue
            at = found.get("at") or [0, 0]
            sz = found.get("size") or [0, 0]
            fl = bool(found.get("floating"))
            fs = int(found.get("fullscreen") or 0)
            pos = abs(int(at[0]) - x) <= 40 and abs(int(at[1]) - y) <= 40
            size = abs(int(sz[0]) - w) / max(w, 1) <= 0.2 and abs(int(sz[1]) - h) / max(h, 1) <= 0.2
            log("FINAL", r, "at", at, "size", sz, "float", fl, "fs", fs)
            if not (pos and size and fl and fs == 0):
                ok2 = False
                log("FINAL_OFF", r)
        log("CORRECT_OK" if ok2 else "CORRECT_STILL_OFF")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("ARRANGE_FAIL", e)
        raise
