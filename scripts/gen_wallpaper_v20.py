"""v20: photographic wet-night plate full-frame + SVG-faithful mark + droplet reflections.

Fixes vs v19 (guest feedback):
1. Background = photographic plate (sky + wet asphalt), NOT procedural stars/nebulae.
   Prefer high-res 1920×1080 plate; Lanczos (or better) upscale to 3440×1440 / 5120×2160.
   Ultrawide: height-fit + mirrored side pads (no horizontal stretch; no sky/floor crop).
2. Logo: SVG-faithful bar spacing (Δx=4), supersampled ~3–4× then Lanczos down.
3. Balls: soft radial glow smaller than v18 rings (r*3.4); extra transparent pad so
   glow is not clipped; crisp white cores.
4. Wet droplet Switchbay color reflections under the logo (v17 spirit) — enhance the
   photo’s natural wet beads, do not invent a new floor.
5. Optional very light grain only.
"""
from __future__ import annotations

import io
import json
import math
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "themes" / "switchbay" / "backgrounds"
EXPORT_V17 = REPO / "scripts" / "wallpaper-playground-export-v17.json"

# Prefer higher-res plate (1920×1080); fall back to asset JPEG / archived copy.
BG_CANDIDATES = [
    Path("/workspace/wallpaper-playground/bg-16x9.png"),
    OUT_DIR / "archive" / "bg-source-16x9.png",
    Path(
        "/home/box/agent-data/agents/4deed81b-eba7-47c9-8fb0-f1684b45907d/assets/"
        "3e1bdcc8217b2106b1622c911a441c95dc2204d5eedf02ca91e21324dabaaf26.png"
    ),
    Path(
        "/home/box/sand-data/agents/4deed81b-eba7-47c9-8fb0-f1684b45907d/assets/"
        "3e1bdcc8217b2106b1622c911a441c95dc2204d5eedf02ca91e21324dabaaf26.png"
    ),
]

COLORS = ["#5a2bf0", "#2079ab", "#12996a", "#f08a12", "#a83e7e"]
BALL_RGB = (215, 219, 226)
# Crisp white cores on top of soft balls
BALL_CORE_RGB = (255, 255, 255)

# SVG-faithful geometry (okbay-mark-nobox.svg): spacing Δx=4, not v19's 3.3
STARTS = [(5.0, 27.0), (9.0, 27.0), (13.0, 27.0), (17.0, 27.0), (21.0, 27.0)]
ENDS = [(11.0, 7.0), (15.0, 7.0), (19.0, 7.0), (23.0, 7.0), (27.0, 7.0)]
BALLS = [(4.0, 28.0), (28.0, 4.0)]
# Slightly under SVG 3.2 so round caps stay clearly separated at spacing 4
SVG_STROKE = 2.85
SVG_BALL_R = 2.2

# Glow: v18 used r_dot*3.4 (large rings). Smaller + padded.
GLOW_RADIUS_MUL = 2.05
GLOW_PEAK_A = 105
GLOW_PAD_MUL = 1.85  # transparent pad beyond glow radius before crop

# Plate floor ratio from playground export (16x9 floor_y/H ≈ 0.715)
PLATE_FLOOR_RATIO = 772 / 1080

SUPERSAMPLE = 4  # render mark ~4× then Lanczos down


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def resolve_bg() -> Path:
    for p in BG_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("no photographic plate found among BG_CANDIDATES")


def _lanczos_resize(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    """High-quality Lanczos; try ImageMagick convert if available for large ups."""
    if im.size == size:
        return im
    return im.resize(size, Image.Resampling.LANCZOS)


def plate_to_canvas(src: Image.Image, W: int, H: int) -> Image.Image:
    """Fit photographic plate to canvas without stretching.

    - Height-fit (preserve aspect) so sky + wet floor stay full-frame vertically.
    - If narrower than ultrawide: mirror-pad left/right from plate edges.
    - If wider (e.g. square target): center-crop horizontally.
    """
    src = src.convert("RGBA")
    sw, sh = src.size
    scale = H / sh
    nw = max(1, int(round(sw * scale)))
    nh = H
    scaled = _lanczos_resize(src, (nw, nh))

    if nw == W:
        return scaled
    if nw > W:
        # Center crop
        x0 = (nw - W) // 2
        return scaled.crop((x0, 0, x0 + W, H))

    # Mirror-pad sides to ultrawide
    out = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    x_off = (W - nw) // 2
    out.paste(scaled, (x_off, 0))
    left_need = x_off
    right_need = W - (x_off + nw)
    # Build mirrored strips from edge columns
    if left_need > 0:
        strip_w = min(nw, left_need)
        left = scaled.crop((0, 0, strip_w, H)).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        # Tile if pad wider than one strip
        x = x_off
        while left_need > 0:
            use = min(strip_w, left_need)
            piece = left.crop((strip_w - use, 0, strip_w, H)) if use < strip_w else left
            x -= use
            out.paste(piece, (x, 0))
            left_need -= use
            # next tile: flip again from current edge for continuity
            left = piece.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            strip_w = piece.size[0]
    if right_need > 0:
        strip_w = min(nw, right_need)
        right = scaled.crop((nw - strip_w, 0, nw, H)).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        x = x_off + nw
        while right_need > 0:
            use = min(strip_w, right_need)
            piece = right.crop((0, 0, use, H))
            out.paste(piece, (x, 0))
            x += use
            right_need -= use
            right = piece.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            strip_w = piece.size[0]
    return out


def light_grain(img: Image.Image, amount: float = 4.5, seed: int = 20) -> Image.Image:
    """Optional very light film grain (does not replace photo texture)."""
    rng = np.random.default_rng(seed)
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    noise = rng.standard_normal(arr.shape[:2]).astype(np.float32) * amount
    arr = np.clip(arr + noise[:, :, None], 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def mark_svg_bytes(stroke: float = SVG_STROKE) -> bytes:
    lines = []
    for (x1, y1), (x2, y2), c in zip(STARTS, ENDS, COLORS):
        lines.append(
            f'<line x1="{x1:.4f}" y1="{y1:.4f}" x2="{x2:.4f}" y2="{y2:.4f}" stroke="{c}"/>'
        )
    body = "\n      ".join(lines)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 384">
  <g transform="translate(0 0) scale(12)">
    <g stroke-linecap="round" stroke-width="{stroke}" fill="none">
      {body}
    </g>
  </g>
</svg>""".encode()


def soft_radial_glow(
    size: int,
    cx: float,
    cy: float,
    radius: float,
    color=(235, 238, 245),
    peak_a: int = GLOW_PEAK_A,
) -> Image.Image:
    yy, xx = np.ogrid[0:size, 0:size]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(1e-6, radius)
    fall = np.clip(1.0 - dist, 0.0, 1.0)
    fall = fall * fall
    a = (fall * peak_a).astype(np.uint8)
    layer = np.zeros((size, size, 4), dtype=np.uint8)
    layer[:, :, 0] = color[0]
    layer[:, :, 1] = color[1]
    layer[:, :, 2] = color[2]
    layer[:, :, 3] = a
    return Image.fromarray(layer, "RGBA")


def draw_mark(size: int) -> Image.Image:
    """SVG-faithful parallel bars + soft glow balls; supersample then Lanczos down."""
    # Parallel + spacing checks
    dx0 = ENDS[0][0] - STARTS[0][0]
    dy0 = ENDS[0][1] - STARTS[0][1]
    for s, e in zip(STARTS, ENDS):
        assert abs((e[0] - s[0]) - dx0) < 1e-9
        assert abs((e[1] - s[1]) - dy0) < 1e-9
    for i in range(1, len(STARTS)):
        assert abs((STARTS[i][0] - STARTS[i - 1][0]) - 4.0) < 1e-9

    S = max(1024, int(size * SUPERSAMPLE))
    S = min(S, 4096)
    png = cairosvg.svg2png(bytestring=mark_svg_bytes(), output_width=S, output_height=S)
    bars = Image.open(io.BytesIO(png)).convert("RGBA")

    scale = S / 384.0
    r_dot = SVG_BALL_R * 12.0 * scale
    glow_r = r_dot * GLOW_RADIUS_MUL
    balls_px = [(u * 12.0 * scale, v * 12.0 * scale) for u, v in BALLS]

    # Extra canvas pad so glow never hits the SVG viewBox edge before crop
    pad_px = int(math.ceil(glow_r * GLOW_PAD_MUL)) + max(16, S // 64)
    canvas_s = S + 2 * pad_px
    glow = Image.new("RGBA", (canvas_s, canvas_s), (0, 0, 0, 0))
    for cx, cy in balls_px:
        glow = Image.alpha_composite(
            glow,
            soft_radial_glow(canvas_s, cx + pad_px, cy + pad_px, glow_r, peak_a=GLOW_PEAK_A),
        )

    bars_p = Image.new("RGBA", (canvas_s, canvas_s), (0, 0, 0, 0))
    bars_p.paste(bars, (pad_px, pad_px))

    ball_layer = Image.new("RGBA", (canvas_s, canvas_s), (0, 0, 0, 0))
    bd = ImageDraw.Draw(ball_layer)
    for cx, cy in balls_px:
        x, y = cx + pad_px, cy + pad_px
        bd.ellipse([x - r_dot, y - r_dot, x + r_dot, y + r_dot], fill=BALL_RGB + (255,))
        # Crisp white core highlight
        hr = max(2.0, r_dot * 0.38)
        hx = x - r_dot * 0.22
        hy = y - r_dot * 0.28
        bd.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=BALL_CORE_RGB + (230,))

    out = Image.alpha_composite(glow, bars_p)
    out = Image.alpha_composite(out, ball_layer)

    arr = np.array(out)
    arr[arr[:, :, 3] < 6] = (0, 0, 0, 0)
    out = Image.fromarray(arr, "RGBA")

    a = np.array(out.split()[-1])
    ys, xs = np.where(a > 5)
    if len(xs) == 0:
        return out.resize((size, size), Image.Resampling.LANCZOS)
    # Keep generous transparent pad around glow
    crop_pad = int(math.ceil(glow_r * 0.35)) + max(8, S // 96)
    l = max(0, int(xs.min()) - crop_pad)
    t = max(0, int(ys.min()) - crop_pad)
    r = min(canvas_s, int(xs.max()) + crop_pad + 1)
    b = min(canvas_s, int(ys.max()) + crop_pad + 1)
    out = out.crop((l, t, r, b))

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
    """Extract wet-bead speculars from the photographic floor (v17 spirit)."""
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


def droplet_reflections(base, beads, mark_xy, mark_size, floor_y):
    """Paint Switchbay colors into photo wet beads under the logo (v17 spirit)."""
    W, H = base.size
    mx, my = mark_xy
    mw, mh = mark_size
    x0 = mx - int(mw * 0.06)
    x1 = mx + mw + int(mw * 0.06)
    cx = (x0 + x1) // 2
    reach = min(H, floor_y + int(H * 0.32))
    half = max(24, (x1 - x0) // 2)

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

    beads_hard = beads.point(
        lambda p: min(255, int(p * 1.35)) if p > 28 else (int(p * 0.35) if p > 12 else 0)
    )
    ramp = color_ramp_image(W, H, x0, x1, floor_y, reach)
    bead_gate = ImageChops.multiply(beads_hard, fall)
    r, g, b, a = ramp.split()
    a = ImageChops.multiply(a, bead_gate)
    hot = beads_hard.point(lambda p: min(255, int(p * 1.55)) if p > 45 else 0)
    hot = ImageChops.multiply(hot, fall)
    a2 = ImageChops.lighter(
        a, ImageChops.multiply(a.point(lambda p: min(255, int(p * 1.7))), hot)
    )
    tint = Image.merge("RGBA", (r, g, b, a2)).filter(ImageFilter.GaussianBlur(0.55))
    layer = Image.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)), tint)

    # Soft specular glints along bar colors (enhance, don't invent floor)
    glint = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glint)
    for i, gx_frac in enumerate((0.10, 0.30, 0.50, 0.70, 0.90)):
        gx = mx + int(mw * gx_frac)
        col = hex_rgb(COLORS[i])
        for yy in range(floor_y, min(H, floor_y + int(H * 0.18)), 3):
            gd.ellipse([gx - 2, yy - 1, gx + 2, yy + 3], fill=col + (70,))
    # Soft white under bottom-left ball
    gx0 = mx + int(mw * 0.12)
    for yy in range(floor_y, min(H, floor_y + int(H * 0.14)), 3):
        gd.ellipse([gx0 - 2, yy - 1, gx0 + 2, yy + 3], fill=(220, 225, 235, 85))
    glint = glint.filter(ImageFilter.GaussianBlur(1.15))
    gr, gg, gb, ga = glint.split()
    ga = ImageChops.multiply(ga, bead_gate)
    layer = Image.alpha_composite(layer, Image.merge("RGBA", (gr, gg, gb, ga)))

    layer.paste(Image.new("RGBA", (W, floor_y), (0, 0, 0, 0)), (0, 0))
    return Image.alpha_composite(base.convert("RGBA"), layer)


def map_layout(W: int, H: int, export: dict) -> dict:
    """Map 16x9 export layout to target canvas (height-proportional; mark centered in X)."""
    base = export["16x9"]
    bw, bh = base["canvas"]["w"], base["canvas"]["h"]
    sy = H / bh
    m = base["mark"]
    mw = int(round(m["w"] * sy))
    mh = int(round(m["h"] * sy))
    cx = (m["x"] + m["w"] / 2) / bw
    mx = int(round(cx * W - mw / 2))
    my = int(round(m["y"] * sy))
    # Floor follows plate ratio after height-fit (same vertical mapping as plate)
    floor_y = int(round(PLATE_FLOOR_RATIO * H))
    return {"floor_y": floor_y, "mark": {"x": mx, "y": my, "w": mw, "h": mh}}


def compose(W: int, H: int, layout: dict, out_path: Path, plate: Image.Image, seed: int = 20) -> None:
    floor_y = layout["floor_y"]
    m = layout["mark"]
    mx, my, mw, mh = int(m["x"]), int(m["y"]), int(m["w"]), int(m["h"])
    print(f"compose {W}x{H} floor_y={floor_y} mark=({mx},{my}) {mw}x{mh} -> {out_path.name}")

    base = plate_to_canvas(plate, W, H)
    # Optional very light grain
    base = light_grain(base, amount=3.5, seed=seed)

    beads = droplet_mask(base, floor_y)
    mark = sized_mark(mw, mh)
    composed = droplet_reflections(base, beads, (mx, my), mark.size, floor_y)
    composed.alpha_composite(mark, (mx, my))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    composed.convert("RGB").save(out_path, optimize=True)
    print(f"  wrote {out_path} ({out_path.stat().st_size} bytes)")


def main():
    with open(EXPORT_V17) as f:
        export = json.load(f)

    bg_path = resolve_bg()
    print(f"photographic plate: {bg_path} ({Image.open(bg_path).size})")
    plate = Image.open(bg_path).convert("RGBA")

    targets = [
        (3440, 1440, "1-okbay-night.png", 20),
        (3440, 1440, "okbay-wallpaper-ultrawide-3440x1440.png", 20),
        (3440, 1440, "okbay-wallpaper-ultrawide.png", 20),
        (5120, 2160, "okbay-wallpaper-ultrawide-5120x2160.png", 20),
        (1920, 1080, "okbay-wallpaper-16x9.png", 20),
        (1920, 1080, "okbay-wallpaper-16x9-v17.png", 20),
        (1920, 1080, "omarchy.png", 20),
        (1280, 1280, "okbay-wallpaper-square.png", 21),
        (1280, 1280, "okbay-wallpaper-square-v17.png", 21),
    ]
    extras = [
        (3440, 1440, "okbay-wallpaper-ultrawide-3440x1440-v20.png", 20),
        (5120, 2160, "okbay-wallpaper-ultrawide-5120x2160-v20.png", 20),
        (1920, 1080, "okbay-wallpaper-16x9-v20.png", 20),
        (1280, 1280, "okbay-wallpaper-square-v20.png", 21),
    ]

    for W, H, name, seed in targets + extras:
        if W == 1280 and H == 1280 and "square_mapped" in export:
            cfg = export["square_mapped"]
            layout = {
                "floor_y": int(round(PLATE_FLOOR_RATIO * H)),
                "mark": {
                    "x": int(cfg["mark"]["x"]),
                    "y": int(cfg["mark"]["y"]),
                    "w": int(cfg["mark"]["w"]),
                    "h": int(cfg["mark"]["h"]),
                },
            }
        else:
            layout = map_layout(W, H, export)
        compose(W, H, layout, OUT_DIR / name, plate, seed=seed)

    mark_ref = draw_mark(1024)
    mark_ref.save(OUT_DIR / "okbay-mark-faithful.png")
    print("wrote okbay-mark-faithful.png", mark_ref.size)
    print("done v20")


if __name__ == "__main__":
    main()
