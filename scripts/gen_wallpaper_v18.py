"""v18: native-res night sky + SVG-faithful parallel mark + soft Gaussian ball glow.

Sky is generated at target resolution (no sole upscale of 1280×720 JPEG).
Optional wet-floor plate from the old BG is composited only below floor_y.
Mark: five parallel bars (identical Δx/Δy), thin enough not to overlap,
round caps, flush ends; white balls get blurred glow under crisp discs only.
"""
from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps
import cairosvg
import io

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "themes" / "switchbay" / "backgrounds"
EXPORT_V17 = REPO / "scripts" / "wallpaper-playground-export-v17.json"
BG_SRC = Path(
    "/home/box/sand-data/agents/4deed81b-eba7-47c9-8fb0-f1684b45907d/assets/"
    "3e1bdcc8217b2106b1622c911a441c95dc2204d5eedf02ca91e21324dabaaf26.png"
)
# Fallbacks if asset path moves
BG_FALLBACKS = [
    Path("/workspace/wallpaper-playground/bg-16x9.png"),
    OUT_DIR / "archive" / "bg-source.png",
]

COLORS = ["#5a2bf0", "#2079ab", "#12996a", "#f08a12", "#a83e7e"]
BALL_RGB = (215, 219, 226)
# SVG viewBox unit geometry (scale(12) in okbay-mark-nobox.svg)
STARTS = [(5.0, 27.0), (9.0, 27.0), (13.0, 27.0), (17.0, 27.0), (21.0, 27.0)]
ENDS = [(11.0, 7.0), (15.0, 7.0), (19.0, 7.0), (23.0, 7.0), (27.0, 7.0)]
BALLS = [(4.0, 28.0), (28.0, 4.0)]
SVG_STROKE = 2.55  # under SVG 3.2 / spacing 4 → clear parallel gaps, flush caps
SVG_BALL_R = 2.2
UNIT = 32.0


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def crop_alpha(img: Image.Image, pad: int = 2) -> Image.Image:
    a = img.split()[-1]
    bbox = a.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    return img.crop(
        (max(0, l - pad), max(0, t - pad), min(img.size[0], r + pad), min(img.size[1], b + pad))
    )


def resolve_bg() -> Path:
    if BG_SRC.exists():
        return BG_SRC
    for p in BG_FALLBACKS:
        if p.exists():
            return p
    raise FileNotFoundError("no source BG for wet-floor plate")


def make_sky(W: int, H: int, floor_y: int, seed: int = 18) -> Image.Image:
    """Native-resolution deep blue-black gradient + starfield + soft nebula."""
    rng = np.random.default_rng(seed)
    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]  # (H,1)
    top = np.array([4, 8, 22], dtype=np.float32)
    mid = np.array([10, 18, 42], dtype=np.float32)
    bot = np.array([2, 4, 12], dtype=np.float32)
    col = (1.0 - yy) * top + yy * mid  # (H,3)
    blend = np.clip((yy[:, 0] - 0.55) / 0.45, 0.0, 1.0)[:, None]  # (H,1)
    col = (1.0 - blend) * col + blend * bot
    sky = np.broadcast_to(col[:, None, :], (H, W, 3)).copy()
    # Low-frequency nebula (blurred noise)
    coarse_h, coarse_w = max(24, H // 48), max(48, W // 48)
    noise = rng.standard_normal((coarse_h, coarse_w)).astype(np.float32)
    neb = Image.fromarray(((noise - noise.min()) / max(1e-6, noise.max() - noise.min()) * 255).astype(np.uint8), "L")
    neb = neb.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(radius=max(8, W // 220)))
    neb_a = np.asarray(neb, dtype=np.float32) / 255.0
    fade = (1.0 - yy)  # (H,1)
    tint = np.zeros((H, W, 3), dtype=np.float32)
    tint[:, :, 0] = 18 * neb_a * fade
    tint[:, :, 1] = 10 * neb_a
    tint[:, :, 2] = 28 * neb_a * (0.4 + 0.6 * fade)
    sky = np.clip(sky + tint, 0, 255)

    img = Image.fromarray(sky.astype(np.uint8), "RGB").convert("RGBA")

    # Tiny stars (many)
    star_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(star_layer)
    n_tiny = int(W * H / 1900)
    for _ in range(n_tiny):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, max(1, floor_y - 8)))
        bright = int(rng.integers(90, 200))
        a = int(rng.integers(120, 230))
        sd.point((x, y), fill=(bright, bright + 4, 255, a))
        if rng.random() < 0.08:
            sd.point((x + 1, y), fill=(bright, bright, 255, a // 2))

    # Brighter stars with soft blur
    bright_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bright_layer)
    n_bright = max(48, int(W * H / 75000))
    for _ in range(n_bright):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, max(1, int(floor_y * 0.92))))
        r = float(rng.uniform(1.2, 2.8))
        a = int(rng.integers(160, 255))
        bd.ellipse([x - r, y - r, x + r, y + r], fill=(230, 235, 255, a))
        # faint cross spike
        if rng.random() < 0.35:
            spike = max(3, int(r * 3))
            bd.line([(x - spike, y), (x + spike, y)], fill=(220, 225, 255, a // 3), width=1)
            bd.line([(x, y - spike), (x, y + spike)], fill=(220, 225, 255, a // 3), width=1)
    bright_soft = bright_layer.filter(ImageFilter.GaussianBlur(radius=max(1.2, W / 1800)))
    bright_crisp = bright_layer.filter(ImageFilter.GaussianBlur(radius=0.4))

    out = Image.alpha_composite(img, star_layer)
    out = Image.alpha_composite(out, bright_soft)
    out = Image.alpha_composite(out, bright_crisp)
    # Clear below floor — wet plate owns that region
    if floor_y < H:
        clear = Image.new("RGBA", (W, H - floor_y), (0, 0, 0, 0))
        out.paste(clear, (0, floor_y))
    return out


def wet_floor_plate(W: int, H: int, floor_y: int) -> Image.Image:
    """Carefully upscale only the wet-floor band from the old BG; blend at horizon."""
    src_path = resolve_bg()
    src = Image.open(src_path).convert("RGBA")
    sw, sh = src.size
    src_floor = int(round(0.715 * sh))  # matches v17 export ratio
    band = src.crop((0, src_floor, sw, sh))
    target_h = H - floor_y
    # Upscale wet band to full width; accept softness only here
    band = band.resize((W, target_h), Image.Resampling.LANCZOS)
    # Slight local contrast so beads survive the scale
    band_rgb = ImageOps.autocontrast(band.convert("RGB"), cutoff=1).convert("RGBA")
    band = Image.blend(band, band_rgb, 0.35)

    plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    plate.paste(band, (0, floor_y))

    # Soft horizon veil so sky→floor join isn't a hard seam
    veil_h = max(12, H // 48)
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    for i in range(veil_h):
        t = i / max(1, veil_h - 1)
        # darken slightly just above floor, fade into floor
        y = floor_y - veil_h + i
        if 0 <= y < H:
            a = int(90 * (1 - abs(t - 0.55)))
            vd.line([(0, y), (W, y)], fill=(2, 4, 14, a))
    plate = Image.alpha_composite(plate, veil)
    return plate


def mark_svg_bytes(stroke: float = SVG_STROKE) -> bytes:
    """Bars only (no balls) — balls + glow composited in Python for soft Gaussian/radial glow."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 384">
  <g transform="translate(0 0) scale(12)">
    <g stroke-linecap="round" stroke-width="{stroke}" fill="none">
      <line x1="5" y1="27" x2="11" y2="7" stroke="#5a2bf0"/>
      <line x1="9" y1="27" x2="15" y2="7" stroke="#2079ab"/>
      <line x1="13" y1="27" x2="19" y2="7" stroke="#12996a"/>
      <line x1="17" y1="27" x2="23" y2="7" stroke="#f08a12"/>
      <line x1="21" y1="27" x2="27" y2="7" stroke="#a83e7e"/>
    </g>
  </g>
</svg>""".encode()


def soft_radial_glow(size: int, cx: float, cy: float, radius: float,
                     color=(235, 238, 245), peak_a: int = 115) -> Image.Image:
    """Smooth r^2 falloff disc — no concentric hard rings."""
    yy, xx = np.ogrid[0:size, 0:size]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(1e-6, radius)
    fall = np.clip(1.0 - dist, 0.0, 1.0)
    fall = fall * fall  # smooth
    a = (fall * peak_a).astype(np.uint8)
    layer = np.zeros((size, size, 4), dtype=np.uint8)
    layer[:, :, 0] = color[0]
    layer[:, :, 1] = color[1]
    layer[:, :, 2] = color[2]
    layer[:, :, 3] = a
    return Image.fromarray(layer, "RGBA")


def draw_mark(size: int) -> Image.Image:
    """SVG-faithful parallel bars (Cairo) + soft radial glow under crisp balls.

    Rendered large then downscaled. Stroke < 3.2 so bars do not overlap.
    """
    # High internal resolution for crisp downscale
    S = max(1024, int(size * 3))
    S = min(S, 4096)
    png = cairosvg.svg2png(bytestring=mark_svg_bytes(), output_width=S, output_height=S)
    bars = Image.open(io.BytesIO(png)).convert("RGBA")

    # Verify parallel deltas in unit space
    dx0 = ENDS[0][0] - STARTS[0][0]
    dy0 = ENDS[0][1] - STARTS[0][1]
    for s, e in zip(STARTS, ENDS):
        assert abs((e[0] - s[0]) - dx0) < 1e-9
        assert abs((e[1] - s[1]) - dy0) < 1e-9

    scale = S / 384.0  # viewBox units → pixels (SVG already scale(12))
    r_dot = SVG_BALL_R * 12.0 * scale
    balls_px = [(u * 12.0 * scale, v * 12.0 * scale) for u, v in BALLS]

    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    for cx, cy in balls_px:
        glow = Image.alpha_composite(
            glow, soft_radial_glow(S, cx, cy, r_dot * 3.4, peak_a=125)
        )

    ball_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bd = ImageDraw.Draw(ball_layer)
    for cx, cy in balls_px:
        bd.ellipse([cx - r_dot, cy - r_dot, cx + r_dot, cy + r_dot], fill=BALL_RGB + (255,))

    out = Image.alpha_composite(glow, bars)
    out = Image.alpha_composite(out, ball_layer)

    # Kill cairo/PNG fringe so mark box never reads as a hard square shell
    arr = np.array(out)
    arr[arr[:, :, 3] < 8] = (0, 0, 0, 0)
    out = Image.fromarray(arr, "RGBA")

    # Tight crop on meaningful alpha
    arr = np.array(out.split()[-1])
    ys, xs = np.where(arr > 10)
    if len(xs) == 0:
        return out.resize((size, size), Image.Resampling.LANCZOS)
    pad = max(4, S // 128)
    l = max(0, int(xs.min()) - pad)
    t = max(0, int(ys.min()) - pad)
    r = min(S, int(xs.max()) + pad + 1)
    b = min(S, int(ys.max()) + pad + 1)
    out = out.crop((l, t, r, b))
    # Downscale so longest side ~= size
    side = max(out.size)
    if side != size:
        sc = size / side
        out = out.resize(
            (max(1, int(round(out.size[0] * sc))), max(1, int(round(out.size[1] * sc)))),
            Image.Resampling.LANCZOS,
        )
    return out


def sized_mark(w: int, h: int) -> Image.Image:
    side = max(w, h)
    mark = draw_mark(max(side, 768))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # Fit mark into box preserving aspect
    mw, mh = mark.size
    scale = min(w / mw, h / mh)
    nw, nh = max(1, int(round(mw * scale))), max(1, int(round(mh * scale)))
    if (nw, nh) != mark.size:
        mark = mark.resize((nw, nh), Image.Resampling.LANCZOS)
    ox = (w - mark.size[0]) // 2
    oy = (h - mark.size[1]) // 2
    canvas.alpha_composite(mark, (ox, oy))
    return canvas


def droplet_mask(bg_rgba: Image.Image, floor_y: int) -> Image.Image:
    W, H = bg_rgba.size
    floor = bg_rgba.crop((0, floor_y, W, H)).convert("L")
    hi = ImageOps.autocontrast(floor)
    detail = ImageChops.subtract(hi, hi.filter(ImageFilter.GaussianBlur(3)))
    beads = detail.point(lambda p: 255 if p > 14 else (int(p * 12) if p > 6 else 0))
    beads = beads.filter(ImageFilter.GaussianBlur(0.4))
    mask = Image.new("L", (W, H), 0)
    mask.paste(beads, (0, floor_y))
    return mask


def color_ramp_image(W, H, x0, x1, floor_y, reach):
    cols = np.array([hex_rgb(c) for c in COLORS], dtype=np.float32)
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    x0c, x1c = max(0, x0), min(W, x1)
    y1 = min(H, reach)
    if x1c <= x0c or y1 <= floor_y:
        return Image.fromarray(arr, "RGBA")
    span = max(1, x1 - x0)
    xs = np.arange(x0c, x1c)
    u = (xs - x0) / span
    u = np.clip(u, 0, 0.9999)
    idx = np.floor(u * len(cols)).astype(int)
    f = (u * len(cols) - idx).astype(np.float32)
    c0 = cols[idx]
    c1 = cols[np.minimum(idx + 1, len(cols) - 1)]
    rgb = c0 * (1 - f)[:, None] + c1 * f[:, None]
    ys = np.arange(floor_y, y1)
    t = (ys - floor_y) / max(1, reach - floor_y)
    fade = (255 * ((1 - t) ** 0.85)).astype(np.uint8)
    block = np.zeros((y1 - floor_y, x1c - x0c, 4), dtype=np.uint8)
    block[:, :, :3] = rgb[None, :, :].astype(np.uint8)
    block[:, :, 3] = fade[:, None]
    arr[floor_y:y1, x0c:x1c] = block
    return Image.fromarray(arr, "RGBA")


def droplet_reflections(base, mark_xy, mark_size, floor_y):
    W, H = base.size
    beads = droplet_mask(base, floor_y)
    mx, my = mark_xy
    mw, mh = mark_size
    x0 = mx - int(mw * 0.05)
    x1 = mx + mw + int(mw * 0.05)
    cx = (x0 + x1) // 2
    reach = min(H, floor_y + int(H * 0.32))
    half = max(20, (x1 - x0) // 2)
    fall_a = np.zeros((H, W), dtype=np.float32)
    for y in range(floor_y, reach):
        t = (y - floor_y) / max(1, reach - floor_y)
        row = 255 * ((1 - t) ** 0.7)
        h = int(half * (0.55 + 0.45 * (1 - t)))
        if h < 1:
            continue
        x_lo, x_hi = max(0, cx - h), min(W, cx + h)
        xs = np.arange(x_lo, x_hi)
        dx = np.abs(xs - cx) / h
        a = row * ((1 - dx * dx) ** 1.5)
        fall_a[y, x_lo:x_hi] = np.maximum(fall_a[y, x_lo:x_hi], a)
    fall = Image.fromarray(np.clip(fall_a, 0, 255).astype(np.uint8), "L")
    fall = fall.filter(ImageFilter.GaussianBlur(7))
    fall.paste(0, (0, 0, W, floor_y))

    ramp = color_ramp_image(W, H, x0, x1, floor_y, reach)
    bead_gate = ImageChops.multiply(beads, fall)
    r, g, b, a = ramp.split()
    a = ImageChops.multiply(a, bead_gate)
    hot = beads.point(lambda p: min(255, int(p * 1.4)) if p > 40 else 0)
    hot = ImageChops.multiply(hot, fall)
    a2 = ImageChops.lighter(a, ImageChops.multiply(a.point(lambda p: min(255, int(p * 1.6))), hot))
    tint = Image.merge("RGBA", (r, g, b, a2)).filter(ImageFilter.GaussianBlur(0.6))
    layer = Image.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)), tint)
    layer.paste(Image.new("RGBA", (W, floor_y), (0, 0, 0, 0)), (0, 0))
    return Image.alpha_composite(base.convert("RGBA"), layer)


def map_layout(W: int, H: int, export: dict) -> dict:
    """Map 16x9 playground layout onto arbitrary canvas (height-primary mark scale)."""
    base = export["16x9"]
    bw, bh = base["canvas"]["w"], base["canvas"]["h"]
    sx, sy = W / bw, H / bh
    # Keep mark aspect; scale by height so ultrawide doesn't inflate logo width oddly
    s = sy
    m = base["mark"]
    mw = int(round(m["w"] * s))
    mh = int(round(m["h"] * s))
    # Center horizontally using original relative center
    cx = (m["x"] + m["w"] / 2) / bw
    mx = int(round(cx * W - mw / 2))
    my = int(round(m["y"] * sy))
    floor_y = int(round(base["floor_y"] * sy))
    return {"floor_y": floor_y, "mark": {"x": mx, "y": my, "w": mw, "h": mh}}


def compose(W: int, H: int, layout: dict, out_path: Path, seed: int = 18) -> None:
    floor_y = layout["floor_y"]
    m = layout["mark"]
    mx, my, mw, mh = int(m["x"]), int(m["y"]), int(m["w"]), int(m["h"])
    print(f"compose {W}x{H} floor_y={floor_y} mark=({mx},{my}) {mw}x{mh} -> {out_path.name}")

    sky = make_sky(W, H, floor_y, seed=seed)
    floor = wet_floor_plate(W, H, floor_y)
    # Fill floor region under sky clear with dark base then wet plate
    base = sky.copy()
    dark = Image.new("RGBA", (W, H - floor_y), (2, 4, 12, 255))
    base.paste(dark, (0, floor_y))
    base = Image.alpha_composite(base, floor)

    mark = sized_mark(mw, mh)
    composed = droplet_reflections(base, (mx, my), mark.size, floor_y)
    composed.alpha_composite(mark, (mx, my))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    composed.convert("RGB").save(out_path, optimize=True)
    print(f"  wrote {out_path} ({out_path.stat().st_size} bytes)")


def main():
    with open(EXPORT_V17) as f:
        export = json.load(f)

    targets = [
        (3440, 1440, "1-okbay-night.png", 18),
        (3440, 1440, "okbay-wallpaper-ultrawide-3440x1440.png", 18),
        (3440, 1440, "okbay-wallpaper-ultrawide.png", 18),
        (5120, 2160, "okbay-wallpaper-ultrawide-5120x2160.png", 18),
        (1920, 1080, "okbay-wallpaper-16x9.png", 18),
        (1920, 1080, "okbay-wallpaper-16x9-v17.png", 18),  # keep name; content is v18
        (1920, 1080, "omarchy.png", 18),
        (1280, 1280, "okbay-wallpaper-square.png", 19),
        (1280, 1280, "okbay-wallpaper-square-v17.png", 19),
    ]

    # Also write v18-named copies for clarity
    extras = [
        (3440, 1440, "okbay-wallpaper-ultrawide-3440x1440-v18.png", 18),
        (5120, 2160, "okbay-wallpaper-ultrawide-5120x2160-v18.png", 18),
        (1920, 1080, "okbay-wallpaper-16x9-v18.png", 18),
        (1280, 1280, "okbay-wallpaper-square-v18.png", 19),
    ]

    for W, H, name, seed in targets + extras:
        if W == 1280 and H == 1280 and "square_mapped" in export:
            # Use square export mapping
            cfg = export["square_mapped"]
            layout = {
                "floor_y": int(cfg["floor_y"]),
                "mark": {
                    "x": int(cfg["mark"]["x"]),
                    "y": int(cfg["mark"]["y"]),
                    "w": int(cfg["mark"]["w"]),
                    "h": int(cfg["mark"]["h"]),
                },
            }
        else:
            layout = map_layout(W, H, export)
        compose(W, H, layout, OUT_DIR / name, seed=seed)

    # High-res mark reference (no glow rings)
    mark_ref = draw_mark(1024)
    mark_ref.save(OUT_DIR / "okbay-mark-faithful.png")
    print("wrote okbay-mark-faithful.png", mark_ref.size)
    print("done v18")


if __name__ == "__main__":
    main()
