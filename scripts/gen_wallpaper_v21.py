"""v21: EDSR-upscaled photo plate + flush parallel bars + tiny crisp end dots (no halo).

Fixes vs v20 (guest feedback):
1. Photographic plate still soft/low-res → OpenCV EDSR x2 (tiled) to 3840×2160, cached,
   then height-fit + mirror pads (fallback: ESPCN x2 / multi-pass Lanczos+unsharp).
2. Large grey orbs rejected → only two tiny silver/white dots, zero glow/halo.
3. Bottom-left dot nudged a few px left; top-right a few px right (outward).
4. Bars: five perfectly parallel diagonals, flush tops/bottoms, tightened spacing
   (~3.35; still > stroke → no overlap), supersampled.
5. Keep droplet Switchbay color reflections on the photo floor (v17/v20 spirit).
6. Never boxed icon frame.
"""
from __future__ import annotations

import io
import json
import math
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "themes" / "switchbay" / "backgrounds"
ARCHIVE = OUT_DIR / "archive"
EXPORT_V17 = REPO / "scripts" / "wallpaper-playground-export-v17.json"

# Cached EDSR x2 plate (3840×2160). Prefer this.
CACHE_EDSR2X = ARCHIVE / "bg-source-16x9-edsr2x.png"
BG_SOURCE_CANDIDATES = [
    Path("/workspace/wallpaper-playground/bg-16x9.png"),
    ARCHIVE / "bg-source-16x9.png",
]
EDSR_MODEL = Path("/tmp/upscale-tools/cv2models/EDSR_x2.pb")
ESPCN_MODEL = Path("/tmp/upscale-tools/cv2models/ESPCN_x2.pb")

COLORS = ["#5a2bf0", "#2079ab", "#12996a", "#f08a12", "#a83e7e"]
# Tiny crisp silver/white — not large grey orbs
DOT_RGB = (232, 236, 242)
DOT_CORE_RGB = (255, 255, 255)

# Tightened pitch vs SVG Δx=4; still > stroke → flush, no overlap
BAR_SPACING = 3.35
BAR_CX = 13.0
START_Y, END_Y = 27.0, 7.0
BAR_DX, BAR_DY = 6.0, -20.0  # identical → parallel + horizontally aligned tops/bottoms
SVG_STROKE = 2.55
# Tiny dots (SVG ball was 2.2 — far too large as wallpaper orbs)
DOT_R = 0.40
# Outward nudge in SVG units (~few px at wallpaper scale after *12*scale)
DOT_NUDGE_X = 0.70  # BL further left, TR further right
DOT_NUDGE_Y = 0.20

PLATE_FLOOR_RATIO = 772 / 1080
SUPERSAMPLE = 4


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def bar_geometry():
    """Five parallel bars, flush Y tops/bottoms, tightened X spacing; two end dots."""
    offsets = [-2, -1, 0, 1, 2]
    starts = [(BAR_CX + o * BAR_SPACING, START_Y) for o in offsets]
    ends = [(sx + BAR_DX, sy + BAR_DY) for sx, sy in starts]
    # Outward nudge: BL left, TR right
    s0, e4 = starts[0], ends[-1]
    balls = [
        (s0[0] - 1.0 - DOT_NUDGE_X, s0[1] + 1.0 + DOT_NUDGE_Y),
        (e4[0] + 1.0 + DOT_NUDGE_X, e4[1] - 1.0 - DOT_NUDGE_Y),
    ]
    return starts, ends, balls


def resolve_source_plate() -> Path:
    for p in BG_SOURCE_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("no photographic plate among BG_SOURCE_CANDIDATES")


def _lanczos_unsharp(im: Image.Image, size: tuple[int, int], amount: float = 1.35) -> Image.Image:
    """Multi-pass Lanczos toward target + unsharp — CPU fallback when DNN unavailable."""
    cur = im.convert("RGBA")
    tw, th = size
    # Step up in ≤2× jumps for better Lanczos quality
    while cur.size[0] < tw * 0.98 or cur.size[1] < th * 0.98:
        nw = min(tw, max(cur.size[0] * 2, int(cur.size[0] * 1.75)))
        nh = min(th, max(cur.size[1] * 2, int(cur.size[1] * 1.75)))
        if (nw, nh) == cur.size:
            break
        cur = cur.resize((nw, nh), Image.Resampling.LANCZOS)
    if cur.size != size:
        cur = cur.resize(size, Image.Resampling.LANCZOS)
    # Unsharp mask
    blur = cur.filter(ImageFilter.GaussianBlur(radius=1.1))
    # amount blend: sharp = cur + amount*(cur-blur)
    arr = np.asarray(cur, dtype=np.float32)
    brr = np.asarray(blur, dtype=np.float32)
    out = np.clip(arr + amount * (arr - brr), 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def _dnn_upscale_x2(src_path: Path, out_path: Path, model_path: Path, model_name: str) -> bool:
    """Tiled OpenCV dnn_superres x2. Returns True on success."""
    try:
        import cv2
        from cv2 import dnn_superres
    except Exception as e:
        print(f"dnn_superres unavailable: {e}")
        return False
    if not model_path.exists():
        print(f"model missing: {model_path}")
        return False

    img = cv2.imread(str(src_path), cv2.IMREAD_COLOR)
    if img is None:
        return False
    h, w = img.shape[:2]
    scale = 2
    # ESPCN is light — one shot; EDSR needs tiles
    sr = dnn_superres.DnnSuperResImpl_create()
    sr.readModel(str(model_path))
    sr.setModel(model_name, scale)

    if model_name == "espcn":
        up = sr.upsample(img)
    else:
        tile, pad = 480, 32
        out_f = np.zeros((h * scale, w * scale, 3), dtype=np.float32)
        weight = np.zeros((h * scale, w * scale), dtype=np.float32)
        for y0 in range(0, h, tile):
            for x0 in range(0, w, tile):
                y1, x1 = min(h, y0 + tile), min(w, x0 + tile)
                ya, xa = max(0, y0 - pad), max(0, x0 - pad)
                yb, xb = min(h, y1 + pad), min(w, x1 + pad)
                up = sr.upsample(img[ya:yb, xa:xb])
                py0, px0 = ya * scale, xa * scale
                py1, px1 = yb * scale, xb * scale
                ph, pw = up.shape[:2]
                wy = np.ones(ph, dtype=np.float32)
                wx = np.ones(pw, dtype=np.float32)
                fade = min(pad * scale, ph // 3, pw // 3)
                if fade > 0:
                    ramp = np.linspace(0.02, 1.0, fade, dtype=np.float32)
                    wy[:fade] *= ramp
                    wy[-fade:] *= ramp[::-1]
                    wx[:fade] *= ramp
                    wx[-fade:] *= ramp[::-1]
                ww = wy[:, None] * wx[None, :]
                out_f[py0:py1, px0:px1] += up.astype(np.float32) * ww[:, :, None]
                weight[py0:py1, px0:px1] += ww
        up = np.clip(out_f / np.maximum(weight[:, :, None], 1e-6), 0, 255).astype(np.uint8)

    blur = cv2.GaussianBlur(up, (0, 0), 1.05)
    sharp = cv2.addWeighted(up, 1.4, blur, -0.4, 0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), sharp, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    print(f"cached {model_name} x2 -> {out_path} {sharp.shape}")
    return True


def ensure_upscaled_plate() -> Image.Image:
    """Return best available upscaled plate (prefer EDSR cache)."""
    if CACHE_EDSR2X.exists():
        im = Image.open(CACHE_EDSR2X).convert("RGBA")
        print(f"using cached EDSR plate {CACHE_EDSR2X} {im.size}")
        return im

    src = resolve_source_plate()
    print(f"upscaling source {src} …")
    # Prefer EDSR, then ESPCN, then Lanczos+unsharp
    if _dnn_upscale_x2(src, CACHE_EDSR2X, EDSR_MODEL, "edsr"):
        return Image.open(CACHE_EDSR2X).convert("RGBA")
    espcn_cache = ARCHIVE / "bg-source-16x9-espcn2x.png"
    if _dnn_upscale_x2(src, espcn_cache, ESPCN_MODEL, "espcn"):
        return Image.open(espcn_cache).convert("RGBA")

    src_im = Image.open(src).convert("RGBA")
    tw, th = src_im.size[0] * 2, src_im.size[1] * 2
    up = _lanczos_unsharp(src_im, (tw, th), amount=1.45)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    lanczos_cache = ARCHIVE / "bg-source-16x9-lanczos2x.png"
    up.convert("RGB").save(lanczos_cache, optimize=True)
    print(f"cached Lanczos+unsharp -> {lanczos_cache} {up.size}")
    return up


def plate_to_canvas(src: Image.Image, W: int, H: int) -> Image.Image:
    """Height-fit photographic plate; mirror-pad sides for ultrawide; center-crop if wider."""
    src = src.convert("RGBA")
    sw, sh = src.size
    scale = H / sh
    nw = max(1, int(round(sw * scale)))
    nh = H
    scaled = src.resize((nw, nh), Image.Resampling.LANCZOS) if src.size != (nw, nh) else src
    # Light unsharp after downscale from oversampled plate
    if sw >= W * 1.15 or sh >= H * 1.15:
        blur = scaled.filter(ImageFilter.GaussianBlur(radius=0.7))
        arr = np.asarray(scaled, dtype=np.float32)
        brr = np.asarray(blur, dtype=np.float32)
        scaled = Image.fromarray(np.clip(arr + 0.55 * (arr - brr), 0, 255).astype(np.uint8), "RGBA")

    if nw == W:
        return scaled
    if nw > W:
        x0 = (nw - W) // 2
        return scaled.crop((x0, 0, x0 + W, H))

    out = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    x_off = (W - nw) // 2
    out.paste(scaled, (x_off, 0))
    left_need = x_off
    right_need = W - (x_off + nw)
    if left_need > 0:
        strip_w = min(nw, left_need)
        left = scaled.crop((0, 0, strip_w, H)).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        x = x_off
        while left_need > 0:
            use = min(strip_w, left_need)
            piece = left.crop((strip_w - use, 0, strip_w, H)) if use < strip_w else left
            x -= use
            out.paste(piece, (x, 0))
            left_need -= use
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


def light_grain(img: Image.Image, amount: float = 3.0, seed: int = 21) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    noise = rng.standard_normal(arr.shape[:2]).astype(np.float32) * amount
    arr = np.clip(arr + noise[:, :, None], 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def mark_svg_bytes(starts, ends, stroke: float = SVG_STROKE) -> bytes:
    lines = []
    for (x1, y1), (x2, y2), c in zip(starts, ends, COLORS):
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


def draw_mark(size: int) -> Image.Image:
    """SVG-faithful parallel bars + tiny crisp dots; NO glow/halo; supersample."""
    starts, ends, balls = bar_geometry()
    dx0 = ends[0][0] - starts[0][0]
    dy0 = ends[0][1] - starts[0][1]
    for s, e in zip(starts, ends):
        assert abs((e[0] - s[0]) - dx0) < 1e-9
        assert abs((e[1] - s[1]) - dy0) < 1e-9
    for i in range(1, len(starts)):
        assert abs((starts[i][0] - starts[i - 1][0]) - BAR_SPACING) < 1e-9
    assert BAR_SPACING > SVG_STROKE + 0.4, (BAR_SPACING, SVG_STROKE)
    # Horizontally aligned bottoms/tops
    assert all(abs(s[1] - START_Y) < 1e-9 for s in starts)
    assert all(abs(e[1] - END_Y) < 1e-9 for e in ends)

    S = max(1024, int(size * SUPERSAMPLE))
    S = min(S, 4096)
    png = cairosvg.svg2png(bytestring=mark_svg_bytes(starts, ends), output_width=S, output_height=S)
    bars = Image.open(io.BytesIO(png)).convert("RGBA")

    scale = S / 384.0
    r_dot = DOT_R * 12.0 * scale
    balls_px = [(u * 12.0 * scale, v * 12.0 * scale) for u, v in balls]

    # Modest pad only (no glow) so crop stays tight — never boxed frame
    pad_px = max(8, int(math.ceil(r_dot * 2.5)) + S // 128)
    canvas_s = S + 2 * pad_px
    bars_p = Image.new("RGBA", (canvas_s, canvas_s), (0, 0, 0, 0))
    bars_p.paste(bars, (pad_px, pad_px))

    # Tiny crisp dots — hard edge, no soft radial halo
    ball_layer = Image.new("RGBA", (canvas_s, canvas_s), (0, 0, 0, 0))
    bd = ImageDraw.Draw(ball_layer)
    for cx, cy in balls_px:
        x, y = cx + pad_px, cy + pad_px
        # Flat crisp disk — no specular core, no soft halo
        bd.ellipse(
            [x - r_dot, y - r_dot, x + r_dot, y + r_dot],
            fill=DOT_CORE_RGB + (255,),
        )

    out = Image.alpha_composite(bars_p, ball_layer)

    arr = np.array(out)
    arr[arr[:, :, 3] < 6] = (0, 0, 0, 0)
    out = Image.fromarray(arr, "RGBA")

    a = np.array(out.split()[-1])
    ys, xs = np.where(a > 5)
    if len(xs) == 0:
        return out.resize((size, size), Image.Resampling.LANCZOS)
    crop_pad = max(4, int(math.ceil(r_dot * 1.2)) + S // 192)
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
    """Paint Switchbay colors into photo wet beads under the logo."""
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

    glint = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glint)
    for i, gx_frac in enumerate((0.10, 0.30, 0.50, 0.70, 0.90)):
        gx = mx + int(mw * gx_frac)
        col = hex_rgb(COLORS[i])
        for yy in range(floor_y, min(H, floor_y + int(H * 0.18)), 3):
            gd.ellipse([gx - 2, yy - 1, gx + 2, yy + 3], fill=col + (70,))
    # Soft silver under bottom-left tiny dot (not a large orb reflection)
    gx0 = mx + int(mw * 0.08)
    for yy in range(floor_y, min(H, floor_y + int(H * 0.12)), 3):
        gd.ellipse([gx0 - 1, yy - 1, gx0 + 1, yy + 2], fill=(220, 225, 235, 70))
    glint = glint.filter(ImageFilter.GaussianBlur(1.0))
    gr, gg, gb, ga = glint.split()
    ga = ImageChops.multiply(ga, bead_gate)
    layer = Image.alpha_composite(layer, Image.merge("RGBA", (gr, gg, gb, ga)))

    layer.paste(Image.new("RGBA", (W, floor_y), (0, 0, 0, 0)), (0, 0))
    return Image.alpha_composite(base.convert("RGBA"), layer)


def map_layout(W: int, H: int, export: dict) -> dict:
    base = export["16x9"]
    bw, bh = base["canvas"]["w"], base["canvas"]["h"]
    sy = H / bh
    m = base["mark"]
    mw = int(round(m["w"] * sy))
    mh = int(round(m["h"] * sy))
    cx = (m["x"] + m["w"] / 2) / bw
    mx = int(round(cx * W - mw / 2))
    my = int(round(m["y"] * sy))
    floor_y = int(round(PLATE_FLOOR_RATIO * H))
    return {"floor_y": floor_y, "mark": {"x": mx, "y": my, "w": mw, "h": mh}}


def compose(W: int, H: int, layout: dict, out_path: Path, plate: Image.Image, seed: int = 21) -> None:
    floor_y = layout["floor_y"]
    m = layout["mark"]
    mx, my, mw, mh = int(m["x"]), int(m["y"]), int(m["w"]), int(m["h"])
    print(f"compose {W}x{H} floor_y={floor_y} mark=({mx},{my}) {mw}x{mh} -> {out_path.name}")

    base = plate_to_canvas(plate, W, H)
    base = light_grain(base, amount=2.8, seed=seed)

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

    plate = ensure_upscaled_plate()
    print(f"plate ready: {plate.size}")

    targets = [
        (3440, 1440, "1-okbay-night.png", 21),
        (3440, 1440, "okbay-wallpaper-ultrawide-3440x1440.png", 21),
        (3440, 1440, "okbay-wallpaper-ultrawide.png", 21),
        (5120, 2160, "okbay-wallpaper-ultrawide-5120x2160.png", 21),
        (1920, 1080, "okbay-wallpaper-16x9.png", 21),
        (1920, 1080, "okbay-wallpaper-16x9-v17.png", 21),
        (1920, 1080, "omarchy.png", 21),
        (1280, 1280, "okbay-wallpaper-square.png", 22),
        (1280, 1280, "okbay-wallpaper-square-v17.png", 22),
    ]
    extras = [
        (3440, 1440, "okbay-wallpaper-ultrawide-3440x1440-v21.png", 21),
        (5120, 2160, "okbay-wallpaper-ultrawide-5120x2160-v21.png", 21),
        (1920, 1080, "okbay-wallpaper-16x9-v21.png", 21),
        (1280, 1280, "okbay-wallpaper-square-v21.png", 22),
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
    print("done v21")


if __name__ == "__main__":
    main()
