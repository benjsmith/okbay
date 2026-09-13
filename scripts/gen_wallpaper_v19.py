"""v19: tighter bars, smaller ball glow, near-black sky + palette nebulae, native wet floor.

Fixes vs v18 (guest 3440×1440 feedback):
1. Bar spacing tightened (~3.3 vs SVG 4) — still parallel, flush, no overlap.
2. Ball glow radius shrunk; generous transparent pad so soft halo is not squared off.
3. Near-black astronomical sky with Switchbay-palette nebula wisps; realistic star
   magnitudes (mostly tiny dim points; few bright with soft diffraction — no cartoon crosses).
4. Native-res wet black glass floor + procedural droplets; Switchbay color reflections
   in beads under the logo. Optional light grit blend from old wet plate.
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
BG_SRC = Path(
    "/home/box/sand-data/agents/4deed81b-eba7-47c9-8fb0-f1684b45907d/assets/"
    "3e1bdcc8217b2106b1622c911a441c95dc2204d5eedf02ca91e21324dabaaf26.png"
)
BG_FALLBACKS = [
    Path("/workspace/wallpaper-playground/bg-16x9.png"),
    OUT_DIR / "archive" / "bg-source.png",
]

COLORS = ["#5a2bf0", "#2079ab", "#12996a", "#f08a12", "#a83e7e"]
BALL_RGB = (215, 219, 226)

# Tighten bar pitch: SVG mark uses Δx=4; v19 uses ~3.3 (still > stroke → no overlap).
BAR_SPACING = 3.3
BAR_CX = 13.0  # middle start x (same as SVG middle bar)
START_Y, END_Y = 27.0, 7.0
BAR_DX, BAR_DY = 6.0, -20.0  # identical Δ for all bars → parallel + flush
SVG_STROKE = 2.55
SVG_BALL_R = 2.2
# Glow: was r_dot*3.4 (too large / clipped). Keep soft but compact.
GLOW_RADIUS_MUL = 1.75
GLOW_PEAK_A = 95
GLOW_PAD_MUL = 1.55  # transparent pad beyond glow radius before crop


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def bar_geometry():
    """Five parallel bars with tightened horizontal spacing; balls at corners."""
    offsets = [-2, -1, 0, 1, 2]
    starts = [(BAR_CX + o * BAR_SPACING, START_Y) for o in offsets]
    ends = [(sx + BAR_DX, sy + BAR_DY) for sx, sy in starts]
    # Balls sit slightly outside first-start / last-end (SVG spirit: (4,28) & (28,4))
    s0, e4 = starts[0], ends[-1]
    balls = [(s0[0] - 1.0, s0[1] + 1.0), (e4[0] + 1.0, e4[1] - 3.0)]
    return starts, ends, balls


def resolve_bg() -> Path | None:
    if BG_SRC.exists():
        return BG_SRC
    for p in BG_FALLBACKS:
        if p.exists():
            return p
    return None


def make_sky(W: int, H: int, floor_y: int, seed: int = 19) -> Image.Image:
    """Near-black astronomical sky + Switchbay-palette nebulae + realistic stars."""
    rng = np.random.default_rng(seed)
    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]

    # Near-black base (was too blue in v18)
    top = np.array([0.6, 0.7, 1.6], dtype=np.float32)
    mid = np.array([1.2, 1.4, 2.8], dtype=np.float32)
    bot = np.array([0.4, 0.5, 1.0], dtype=np.float32)
    col = (1.0 - yy) * top + yy * mid
    blend = np.clip((yy[:, 0] - 0.50) / 0.50, 0.0, 1.0)[:, None]
    col = (1.0 - blend) * col + blend * bot
    sky = np.broadcast_to(col[:, None, :], (H, W, 3)).copy()

    # Multi-scale nebula wisps in Switchbay palette (violet/cyan/green/orange/magenta)
    palette = np.array([hex_rgb(c) for c in COLORS], dtype=np.float32)
    fade = np.clip(1.0 - (yy[:, 0] - 0.05) / 0.85, 0.0, 1.0)  # (H,)
    fade = fade * fade  # keep wisps mostly in upper/mid sky

    for i, rgb in enumerate(palette):
        ch, cw = max(16, H // (56 + i * 8)), max(32, W // (56 + i * 8))
        noise = rng.standard_normal((ch, cw)).astype(np.float32)
        # Bias each cloud toward a different horizontal region
        xs = np.linspace(0, 1, cw, dtype=np.float32)
        bias = np.exp(-((xs - (0.12 + i * 0.19)) / 0.22) ** 2)
        noise = noise * (0.55 + 0.9 * bias[None, :])
        neb = Image.fromarray(
            ((noise - noise.min()) / max(1e-6, float(noise.max() - noise.min())) * 255).astype(
                np.uint8
            ),
            "L",
        )
        blur_r = max(10, W // (160 + i * 30))
        neb = neb.resize((W, H), Image.Resampling.BICUBIC).filter(
            ImageFilter.GaussianBlur(radius=blur_r)
        )
        neb_a = np.asarray(neb, dtype=np.float32) / 255.0
        # Soft threshold — keep wisps visible on near-black
        neb_a = np.clip((neb_a - 0.28) / 0.72, 0.0, 1.0) ** 1.15
        strength = 48.0 + 14.0 * (i % 3)  # visible palette wisps
        for c in range(3):
            sky[:, :, c] += rgb[c] / 255.0 * strength * neb_a * fade[:, None]

    # Very faint cool milky dust
    ch, cw = max(12, H // 80), max(24, W // 80)
    dust_n = rng.standard_normal((ch, cw)).astype(np.float32)
    dust = Image.fromarray(
        ((dust_n - dust_n.min()) / max(1e-6, float(dust_n.max() - dust_n.min())) * 255).astype(
            np.uint8
        ),
        "L",
    )
    dust = dust.resize((W, H), Image.Resampling.BICUBIC).filter(
        ImageFilter.GaussianBlur(radius=max(14, W // 140))
    )
    dust_a = np.asarray(dust, dtype=np.float32) / 255.0
    sky[:, :, 0] += 2.0 * dust_a * fade[:, None]
    sky[:, :, 1] += 2.2 * dust_a * fade[:, None]
    sky[:, :, 2] += 3.5 * dust_a * fade[:, None]

    sky = np.clip(sky, 0, 255)
    img = Image.fromarray(sky.astype(np.uint8), "RGB").convert("RGBA")

    # --- Stars: approximate magnitude distribution (many faint, few bright) ---
    sky_h = max(1, floor_y - 4)
    star_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(star_layer)

    # Dim point stars (bulk) — power-law-ish brightness
    n_dim = int(W * H / 2800)
    for _ in range(n_dim):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, sky_h))
        # Most very dim
        mag = float(rng.random() ** 2.4)
        bright = int(40 + mag * 140)
        a = int(50 + mag * 150)
        # slight cool tint
        sd.point((x, y), fill=(bright, bright + 2, min(255, bright + 18), a))

    # Mid stars — 1px with tiny soft glow
    mid_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    md = ImageDraw.Draw(mid_layer)
    n_mid = max(80, int(W * H / 42000))
    for _ in range(n_mid):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, sky_h))
        r = float(rng.uniform(0.6, 1.35))
        a = int(rng.integers(140, 230))
        md.ellipse([x - r, y - r, x + r, y + r], fill=(210, 218, 255, a))
    mid_soft = mid_layer.filter(ImageFilter.GaussianBlur(radius=0.7))

    # Few bright stars — soft diffraction (Gaussian spikes), not chunky crosses
    bright_core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bright_spikes = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bc = ImageDraw.Draw(bright_core)
    bs = ImageDraw.Draw(bright_spikes)
    n_bright = max(18, int(W * H / 160000))
    for _ in range(n_bright):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, max(1, int(sky_h * 0.95))))
        r = float(rng.uniform(1.0, 2.2))
        a = int(rng.integers(200, 255))
        bc.ellipse([x - r, y - r, x + r, y + r], fill=(235, 240, 255, a))
        # Soft diffraction spikes (thin, low alpha — blur will soften)
        spike = max(5, int(r * 5 + rng.uniform(2, 8)))
        col = (220, 228, 255, max(28, a // 5))
        bs.line([(x - spike, y), (x + spike, y)], fill=col, width=1)
        bs.line([(x, y - spike), (x, y + spike)], fill=col, width=1)
        if rng.random() < 0.4:
            # faint diagonal
            d = int(spike * 0.55)
            bs.line([(x - d, y - d), (x + d, y + d)], fill=(210, 220, 255, a // 8), width=1)
            bs.line([(x - d, y + d), (x + d, y - d)], fill=(210, 220, 255, a // 8), width=1)

    spikes_soft = bright_spikes.filter(ImageFilter.GaussianBlur(radius=max(1.0, W / 2200)))
    core_soft = bright_core.filter(ImageFilter.GaussianBlur(radius=max(0.8, W / 2800)))
    core_crisp = bright_core.filter(ImageFilter.GaussianBlur(radius=0.35))

    out = Image.alpha_composite(img, star_layer)
    out = Image.alpha_composite(out, mid_soft)
    out = Image.alpha_composite(out, mid_layer)
    out = Image.alpha_composite(out, spikes_soft)
    out = Image.alpha_composite(out, core_soft)
    out = Image.alpha_composite(out, core_crisp)

    if floor_y < H:
        clear = Image.new("RGBA", (W, H - floor_y), (0, 0, 0, 0))
        out.paste(clear, (0, floor_y))
    return out


def procedural_droplet_mask(W: int, H: int, floor_y: int, seed: int = 19) -> Image.Image:
    """Native-res bead/droplet mask on the wet floor (not from upscaled plate)."""
    rng = np.random.default_rng(seed + 7)
    fh = H - floor_y
    mask = Image.new("L", (W, H), 0)
    layer = Image.new("L", (W, fh), 0)
    d = ImageDraw.Draw(layer)

    n_beads = max(280, int(W * fh / 1400))
    for _ in range(n_beads):
        x = float(rng.uniform(0, W))
        # denser near horizon, sparser deep
        y = float(rng.beta(1.35, 2.8) * fh)
        # size distribution: many tiny, few larger distinct beads
        s = float(rng.random() ** 2.5)
        rx = 0.7 + s * rng.uniform(2.0, 9.5)
        ry = rx * float(rng.uniform(0.5, 1.05))
        a = int(55 + s * 200)
        d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=a)
        # specular highlight speck (reads as a real droplet)
        if s > 0.25 and rng.random() < 0.7:
            hx = x - rx * 0.28
            hy = y - ry * 0.38
            hr = max(0.5, rx * 0.25)
            d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=min(255, a + 80))

    # Clusters / streaks of wetness
    n_clusters = max(12, W // 180)
    for _ in range(n_clusters):
        cx = float(rng.uniform(0, W))
        cy = float(rng.uniform(0, fh * 0.7))
        for __ in range(int(rng.integers(8, 28))):
            x = cx + float(rng.normal(0, 18))
            y = cy + float(rng.normal(0, 10))
            if not (0 <= x < W and 0 <= y < fh):
                continue
            rx = float(rng.uniform(0.8, 3.5))
            ry = rx * float(rng.uniform(0.5, 1.1))
            d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=int(rng.integers(90, 210)))

    layer = layer.filter(ImageFilter.GaussianBlur(radius=0.45))
    mask.paste(layer, (0, floor_y))
    return mask


def wet_floor_native(W: int, H: int, floor_y: int, seed: int = 19) -> tuple[Image.Image, Image.Image]:
    """Native-res wet black glass + droplet mask. Optional grit from old plate."""
    rng = np.random.default_rng(seed)
    fh = max(1, H - floor_y)
    yy = np.linspace(0.0, 1.0, fh, dtype=np.float32)[:, None]

    # Dark reflective glass
    near = np.array([3.0, 4.0, 8.0], dtype=np.float32)
    deep = np.array([1.0, 1.0, 2.0], dtype=np.float32)
    col = (1.0 - yy) * near + yy * deep  # (fh, 3)
    floor = np.broadcast_to(col[:, None, :], (fh, W, 3)).copy()

    # Horizon specular sheen
    sheen = np.exp(-((yy[:, 0] - 0.015) / 0.07) ** 2).astype(np.float32)
    floor[:, :, 0] += sheen[:, None] * 14.0
    floor[:, :, 1] += sheen[:, None] * 16.0
    floor[:, :, 2] += sheen[:, None] * 22.0

    # Low-frequency glass undulation
    ch, cw = max(8, fh // 24), max(16, W // 32)
    und = rng.standard_normal((ch, cw)).astype(np.float32)
    und_img = Image.fromarray(
        ((und - und.min()) / max(1e-6, float(und.max() - und.min())) * 255).astype(np.uint8), "L"
    )
    und_img = und_img.resize((W, fh), Image.Resampling.BICUBIC).filter(
        ImageFilter.GaussianBlur(radius=max(4, W // 400))
    )
    und_a = (np.asarray(und_img, dtype=np.float32) / 255.0 - 0.5) * 10.0
    floor += und_a[:, :, None]

    # Micro grit / noise (native)
    micro = rng.standard_normal((fh, W)).astype(np.float32) * 2.2
    floor += micro[:, :, None]

    floor = np.clip(floor, 0, 255).astype(np.uint8)
    band = Image.fromarray(floor, "RGB").convert("RGBA")

    # Procedural droplet highlights as specular on glass
    beads = procedural_droplet_mask(W, H, floor_y, seed=seed)
    bead_band = beads.crop((0, floor_y, W, H))
    # Brighten bead loci slightly (wet specular)
    bead_rgb = Image.merge(
        "RGBA",
        (
            Image.new("L", (W, fh), 18),
            Image.new("L", (W, fh), 22),
            Image.new("L", (W, fh), 30),
            bead_band.point(lambda p: min(255, int(p * 0.55))),
        ),
    )
    band = Image.alpha_composite(band, bead_rgb)

    # Optional light grit from old wet plate (does not dominate)
    src_path = resolve_bg()
    if src_path is not None:
        src = Image.open(src_path).convert("RGBA")
        sw, sh = src.size
        src_floor = int(round(0.715 * sh))
        old = src.crop((0, src_floor, sw, sh)).resize((W, fh), Image.Resampling.LANCZOS)
        old = ImageOps.autocontrast(old.convert("RGB"), cutoff=2).convert("RGBA")
        # Desaturate + darken so it only adds texture
        old_l = old.convert("L")
        grit = Image.merge(
            "RGBA",
            (
                old_l.point(lambda p: int(p * 0.12)),
                old_l.point(lambda p: int(p * 0.14)),
                old_l.point(lambda p: int(p * 0.18)),
                Image.new("L", (W, fh), 22),  # light grit only
            ),
        )
        band = Image.alpha_composite(band, grit)

    plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    plate.paste(band, (0, floor_y))

    # Soft horizon veil
    veil_h = max(14, H // 42)
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    for i in range(veil_h):
        t = i / max(1, veil_h - 1)
        y = floor_y - veil_h + i
        if 0 <= y < H:
            a = int(70 * (1 - abs(t - 0.6)))
            vd.line([(0, y), (W, y)], fill=(1, 2, 6, a))
    plate = Image.alpha_composite(plate, veil)
    return plate, beads


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
    starts, ends, balls = bar_geometry()
    # Parallel check
    dx0 = ends[0][0] - starts[0][0]
    dy0 = ends[0][1] - starts[0][1]
    for s, e in zip(starts, ends):
        assert abs((e[0] - s[0]) - dx0) < 1e-9
        assert abs((e[1] - s[1]) - dy0) < 1e-9
    # No overlap: spacing > stroke
    assert BAR_SPACING > SVG_STROKE + 0.4, (BAR_SPACING, SVG_STROKE)

    S = max(1024, int(size * 3))
    S = min(S, 4096)
    png = cairosvg.svg2png(
        bytestring=mark_svg_bytes(starts, ends), output_width=S, output_height=S
    )
    bars = Image.open(io.BytesIO(png)).convert("RGBA")

    scale = S / 384.0
    r_dot = SVG_BALL_R * 12.0 * scale
    glow_r = r_dot * GLOW_RADIUS_MUL
    balls_px = [(u * 12.0 * scale, v * 12.0 * scale) for u, v in balls]

    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    for cx, cy in balls_px:
        glow = Image.alpha_composite(
            glow, soft_radial_glow(S, cx, cy, glow_r, peak_a=GLOW_PEAK_A)
        )

    ball_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bd = ImageDraw.Draw(ball_layer)
    for cx, cy in balls_px:
        bd.ellipse(
            [cx - r_dot, cy - r_dot, cx + r_dot, cy + r_dot], fill=BALL_RGB + (255,)
        )

    out = Image.alpha_composite(glow, bars)
    out = Image.alpha_composite(out, ball_layer)

    arr = np.array(out)
    arr[arr[:, :, 3] < 8] = (0, 0, 0, 0)
    out = Image.fromarray(arr, "RGBA")

    # Crop with generous pad so soft glow is not squared off at bbox corners
    a = np.array(out.split()[-1])
    ys, xs = np.where(a > 6)
    if len(xs) == 0:
        return out.resize((size, size), Image.Resampling.LANCZOS)
    pad = int(math.ceil(glow_r * GLOW_PAD_MUL)) + max(8, S // 96)
    l = max(0, int(xs.min()) - pad)
    t = max(0, int(ys.min()) - pad)
    r = min(S, int(xs.max()) + pad + 1)
    b = min(S, int(ys.max()) + pad + 1)
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
    """Paint Switchbay brand colors into water droplets under the logo (v15/v17 spirit)."""
    W, H = base.size
    mx, my = mark_xy
    mw, mh = mark_size
    x0 = mx - int(mw * 0.08)
    x1 = mx + mw + int(mw * 0.08)
    cx = (x0 + x1) // 2
    reach = min(H, floor_y + int(H * 0.34))
    half = max(24, (x1 - x0) // 2)

    fall_a = np.zeros((H, W), dtype=np.float32)
    for y in range(floor_y, reach):
        t = (y - floor_y) / max(1, reach - floor_y)
        row = 255 * ((1 - t) ** 0.65)
        h = int(half * (0.55 + 0.45 * (1 - t)))
        if h < 1:
            continue
        x_lo, x_hi = max(0, cx - h), min(W, cx + h)
        xs = np.arange(x_lo, x_hi)
        dx = np.abs(xs - cx) / h
        a = row * ((1 - dx * dx) ** 1.5)
        fall_a[y, x_lo:x_hi] = np.maximum(fall_a[y, x_lo:x_hi], a)
    fall = Image.fromarray(np.clip(fall_a, 0, 255).astype(np.uint8), "L")
    fall = fall.filter(ImageFilter.GaussianBlur(6))
    fall.paste(0, (0, 0, W, floor_y))

    # Prefer distinct beads over continuous glitter
    beads_hard = beads.point(lambda p: min(255, int(p * 1.35)) if p > 28 else (int(p * 0.35) if p > 12 else 0))
    ramp = color_ramp_image(W, H, x0, x1, floor_y, reach)
    bead_gate = ImageChops.multiply(beads_hard, fall)
    r, g, b, a = ramp.split()
    a = ImageChops.multiply(a, bead_gate)
    hot = beads_hard.point(lambda p: min(255, int(p * 1.6)) if p > 50 else 0)
    hot = ImageChops.multiply(hot, fall)
    a2 = ImageChops.lighter(
        a, ImageChops.multiply(a.point(lambda p: min(255, int(p * 1.85))), hot)
    )
    a2 = a2.point(lambda p: min(255, int(p * 1.25)))
    tint = Image.merge("RGBA", (r, g, b, a2)).filter(ImageFilter.GaussianBlur(0.55))
    layer = Image.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)), tint)

    # Soft specular glints along bar colors
    glint = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glint)
    for i, gx_frac in enumerate((0.08, 0.28, 0.48, 0.68, 0.88)):
        gx = mx + int(mw * gx_frac)
        col = hex_rgb(COLORS[i])
        for yy in range(floor_y, min(H, floor_y + int(H * 0.20)), 4):
            gd.ellipse(
                [gx - 2, yy - 1, gx + 2, yy + 3],
                fill=col + (75,),
            )
    glint = glint.filter(ImageFilter.GaussianBlur(1.1))
    gr, gg, gb, ga = glint.split()
    ga = ImageChops.multiply(ga, bead_gate)
    layer = Image.alpha_composite(layer, Image.merge("RGBA", (gr, gg, gb, ga)))

    layer.paste(Image.new("RGBA", (W, floor_y), (0, 0, 0, 0)), (0, 0))
    return Image.alpha_composite(base.convert("RGBA"), layer)


def map_layout(W: int, H: int, export: dict) -> dict:
    base = export["16x9"]
    bw, bh = base["canvas"]["w"], base["canvas"]["h"]
    sy = H / bh
    s = sy
    m = base["mark"]
    mw = int(round(m["w"] * s))
    mh = int(round(m["h"] * s))
    cx = (m["x"] + m["w"] / 2) / bw
    mx = int(round(cx * W - mw / 2))
    my = int(round(m["y"] * sy))
    floor_y = int(round(base["floor_y"] * sy))
    return {"floor_y": floor_y, "mark": {"x": mx, "y": my, "w": mw, "h": mh}}


def compose(W: int, H: int, layout: dict, out_path: Path, seed: int = 19) -> None:
    floor_y = layout["floor_y"]
    m = layout["mark"]
    mx, my, mw, mh = int(m["x"]), int(m["y"]), int(m["w"]), int(m["h"])
    print(f"compose {W}x{H} floor_y={floor_y} mark=({mx},{my}) {mw}x{mh} -> {out_path.name}")

    sky = make_sky(W, H, floor_y, seed=seed)
    floor, beads = wet_floor_native(W, H, floor_y, seed=seed)
    base = sky.copy()
    dark = Image.new("RGBA", (W, H - floor_y), (1, 1, 2, 255))
    base.paste(dark, (0, floor_y))
    base = Image.alpha_composite(base, floor)

    mark = sized_mark(mw, mh)
    composed = droplet_reflections(base, beads, (mx, my), mark.size, floor_y)
    composed.alpha_composite(mark, (mx, my))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    composed.convert("RGB").save(out_path, optimize=True)
    print(f"  wrote {out_path} ({out_path.stat().st_size} bytes)")


def main():
    with open(EXPORT_V17) as f:
        export = json.load(f)

    targets = [
        (3440, 1440, "1-okbay-night.png", 19),
        (3440, 1440, "okbay-wallpaper-ultrawide-3440x1440.png", 19),
        (3440, 1440, "okbay-wallpaper-ultrawide.png", 19),
        (5120, 2160, "okbay-wallpaper-ultrawide-5120x2160.png", 19),
        (1920, 1080, "okbay-wallpaper-16x9.png", 19),
        (1920, 1080, "okbay-wallpaper-16x9-v17.png", 19),
        (1920, 1080, "omarchy.png", 19),
        (1280, 1280, "okbay-wallpaper-square.png", 20),
        (1280, 1280, "okbay-wallpaper-square-v17.png", 20),
    ]
    extras = [
        (3440, 1440, "okbay-wallpaper-ultrawide-3440x1440-v19.png", 19),
        (5120, 2160, "okbay-wallpaper-ultrawide-5120x2160-v19.png", 19),
        (1920, 1080, "okbay-wallpaper-16x9-v19.png", 19),
        (1280, 1280, "okbay-wallpaper-square-v19.png", 20),
    ]

    for W, H, name, seed in targets + extras:
        if W == 1280 and H == 1280 and "square_mapped" in export:
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

    mark_ref = draw_mark(1024)
    mark_ref.save(OUT_DIR / "okbay-mark-faithful.png")
    print("wrote okbay-mark-faithful.png", mark_ref.size)
    print("done v19")


if __name__ == "__main__":
    main()
