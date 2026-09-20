#!/usr/bin/env python3
"""Place Atlas/Nautilus/Herdr/okstratr into a 2x2 grid on WS_TARGET."""
import json, os, subprocess, time

WS = os.environ.get("WS_TARGET") or "2"

def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    return (r.stdout or "") + (r.stderr or "")

def dsp(arg):
    out = run(["hyprctl", "dispatch", arg]).strip()
    print("DSP", arg[:100], "->", out[:120])
    return out

def clients():
    try:
        return json.loads(subprocess.check_output(["hyprctl", "clients", "-j"], text=True))
    except Exception as e:
        print("clients err", e)
        return []

def mon():
    try:
        mons = json.loads(subprocess.check_output(["hyprctl", "monitors", "-j"], text=True))
        for m in mons:
            if m.get("focused"):
                return m
        return mons[0]
    except Exception:
        return {"width": 1920, "height": 1080, "x": 0, "y": 0}

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

def classify(c):
    b = blob(c)
    if "okbayatlas" in b or ("8766/atlas" in b) or ("atlas" in b and "chromium" in b):
        return "atlas"
    if "nautilus" in b or "org.gnome.nautilus" in b:
        return "nautilus"
    if "herdr" in b:
        return "herdr"
    if "okstratr" in b or "benjsmith.okstratr" in b:
        return "okstratr"
    if "quickshell" in b and ("okstratr" in b or "desk" in b or "panel" in b):
        return "okstratr"
    if c.get("floating") and ("quickshell" in b or str(c.get("class") or "").lower() == "qs"):
        return "okstratr_maybe"
    return None

def wait_roles(timeout=8.0):
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
            maybes.sort(key=lambda c: c.get("focusHistoryID", 0))
            found["okstratr"] = maybes[0]
        best = found
        if all(k in found for k in ("atlas", "nautilus", "herdr", "okstratr")):
            return found
        time.sleep(0.25)
    return best

def move_to_ws(addr, ws):
    dsp(f"movetoworkspacesilent {ws},address:{addr}")

def place(addr, x, y, w, h, name):
    print(f"place {name} {addr} -> {x},{y} {w}x{h}")
    run(["hyprctl", "dispatch", "fullscreen", "0", f"address:{addr}"])
    dsp(f"setfloating address:{addr}")
    time.sleep(0.05)
    dsp(f"resizewindowpixel exact {w} {h},address:{addr}")
    dsp(f"movewindowpixel exact {x} {y},address:{addr}")

def main():
    roles = wait_roles()
    print("roles", {k: (v.get("address"), (v.get("title") or "")[:40]) for k, v in roles.items()})
    for _role, c in list(roles.items()):
        addr = c.get("address")
        if addr:
            move_to_ws(addr, WS)
    time.sleep(0.2)
    roles = wait_roles(timeout=3.0)
    m = mon()
    mx, my = int(m.get("x") or 0), int(m.get("y") or 0)
    W, H = int(m.get("width") or 1920), int(m.get("height") or 1080)
    half_w = W // 2
    half_h = H // 2
    layout = {
        "atlas":    (mx,          my,          half_w, half_h),
        "nautilus": (mx + half_w, my,          W - half_w, half_h),
        "herdr":    (mx,          my + half_h, half_w, H - half_h),
        "okstratr": (mx + half_w, my + half_h, W - half_w, H - half_h),
    }
    for role, (x, y, w, h) in layout.items():
        c = roles.get(role)
        if not c or not c.get("address"):
            print("missing", role)
            continue
        run(["hyprctl", "dispatch", "fullscreen", "0", f"address:{c['address']}"])
        place(c["address"], x, y, w, h, role)
    time.sleep(0.35)
    roles = wait_roles(timeout=2.0)
    for role, (x, y, w, h) in layout.items():
        c = roles.get(role)
        if not c or not c.get("address"):
            continue
        run(["hyprctl", "dispatch", "fullscreen", "0", f"address:{c['address']}"])
        place(c["address"], x, y, w, h, role + "2")
    atlas = roles.get("atlas")
    if atlas and atlas.get("address"):
        dsp(f"focuswindow address:{atlas['address']}")
    print("ARRANGE_DONE")
    for c in clients():
        ws = c.get("workspace") or {}
        print(
            "GEO", c.get("class"), (c.get("title") or "")[:48],
            "ws", ws.get("id"), ws.get("name"),
            "at", c.get("at"), "size", c.get("size"),
            "float", c.get("floating"), "fs", c.get("fullscreen"),
        )

if __name__ == "__main__":
    main()
