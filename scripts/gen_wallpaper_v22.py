"""v22: starfield-only night sky + flush parallel bars + doubled crisp end dots (no wet glass).

Ben 2026-09-20 brief vs v21:
1. Remove wet surface / nanotexture glass entirely — pure procedural starfield.
2. Boost starfield resolution/realism (sharp deep night, parallax-ready detail).
3. Logo geometry memory: five perfectly parallel diagonal bars, flush, tightened
   spacing; only two silver/white end circles — BL nudged left, TR nudged right;
   double the size of the two end balls vs v21 (DOT_R 0.40 → 0.80); tiny crisp
   disks with zero halo/orb glow; never a rounded boxed icon frame.
4. Native 3840×2160 (16x9) and 5120×2160 ultrawide outputs.
"""
from __future__ import annotations

import io
import json
import math
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "themes" / "switchbay" / "backgrounds"
EXPORT_V17 = REPO / "scripts" / "wallpaper-playground-export-v17.json"
SCRATCH = Path("/workspace")

COLORS = ["#5a2bf0", "#2079ab", "#12996a", "#f08a12", "#a83e7e"]
DOT_RGB = (232, 236, 242)
DOT_CORE_RGB = (255, 255, 255)

# Tightened pitch vs SVG Δx=4; still > stroke → flush, no overlap
BAR_SPACING = 3.35
BAR_CX = 13.0
START_Y, END_Y = 27.0, 7.0
BAR_DX, BAR_DY = 6.0, -20.0
SVG_STROKE = 2.55
# v21 DOT_R=0.40; v22 doubles end balls
DOT_R = 0.80
DOT_NUDGE_X = 1.15
DOT_NUDGE_Y = 0.35

SUPERSAMPLE = 4
# Keep mark vertical placement relative to former floor for continuity
LAYOUT_FLOOR_RATIO = 772 / 1080


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def bar_geometry():
    """Five parallel bars, flush Y tops/bottoms, tightened X spacing; two end dots."""
    offsets = [-2, -1, 0, 1, 2]
    starts = [(BAR_CX + o * BAR_SPACING, START_Y) for o in offsets]
    ends = [(sx + BAR_DX, sy + BAR_DY) for sx, sy in starts]
    s0, e4 = starts[0], ends[-1]
    balls = [
        (s0[0] - 1.0 - DOT_NUDGE_X, s0[1] + 1.0 + DOT_NUDGE_Y),
        (e4[0] + 1.0 + DOT_NUDGE_X, e4[1] - 1.0 - DOT_NUDGE_Y),
    ]
    return starts, ends, balls


def make_starfield(W: int, H: int, seed: int = 22) -> Image.Image:
    """Deep near-black astronomical sky — full frame, no wet floor / glass texture."""
    rng = np.random.default_rng(seed)
    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]

    # Near-black vertical gradient (very subtle)
    top = np.array([0.35, 0.40, 0.95], dtype=np.float32)
    mid = np.array([0.55, 0.65, 1.35], dtype=np.float32)
    bot = np.array([0.25, 0.30, 0.70], dtype=np.float32)
    col = (1.0 - yy) * top + yy * mid
    blend = np.clip((yy[:, 0] - 0.45) / 0.55, 0.0, 1.0)[:, None]
    col = (1.0 - blend) * col + blend * bot
    sky = np.broadcast_to(col[:, None, :], (H, W, 3)).copy()

    # Soft palette nebula wisps (low amplitude — parallax-ready depth cue)
    palette = np.array([hex_rgb(c) for c in COLORS], dtype=np.float32)
    fade = np.clip(1.0 - np.abs(yy[:, 0] - 0.38) / 0.72, 0.0, 1.0)
    fade = fade ** 1.35

    for i, rgb in enumerate(palette):
        ch, cw = max(20, H // (48 + i * 6)), max(36, W // (48 + i * 6))
        noise = rng.standard_normal((ch, cw)).astype(np.float32)
        xs = np.linspace(0, 1, cw, dtype=np.float32)
        bias = np.exp(-((xs - (0.10 + i * 0.20)) / 0.24) ** 2)
        noise = noise * (0.50 + 0.95 * bias[None, :])
        neb = Image.fromarray(
            ((noise - noise.min()) / max(1e-6, float(noise.max() - noise.min())) * 255).astype(
                np.uint8
            ),
            "L",
        )
        blur_r = max(14, W // (130 + i * 24))
        neb = neb.resize((W, H), Image.Resampling.BICUBIC).filter(
            ImageFilter.GaussianBlur(radius=blur_r)
        )
        neb_a = np.asarray(neb, dtype=np.float32) / 255.0
        neb_a = np.clip((neb_a - 0.32) / 0.68, 0.0, 1.0) ** 1.25
        strength = 12.0 + 6.0 * (i % 3)  # very subtle depth cue only
        for c in range(3):
            sky[:, :, c] += rgb[c] / 255.0 * strength * neb_a * fade[:, None]

    # Faint milky dust band
    ch, cw = max(14, H // 70), max(28, W // 70)
    dust_n = rng.standard_normal((ch, cw)).astype(np.float32)
    dust = Image.fromarray(
        ((dust_n - dust_n.min()) / max(1e-6, float(dust_n.max() - dust_n.min())) * 255).astype(
            np.uint8
        ),
        "L",
    )
    dust = dust.resize((W, H), Image.Resampling.BICUBIC).filter(
        ImageFilter.GaussianBlur(radius=max(16, W // 120))
    )
    dust_a = np.asarray(dust, dtype=np.float32) / 255.0
    sky[:, :, 0] += 0.7 * dust_a * fade[:, None]
    sky[:, :, 1] += 0.8 * dust_a * fade[:, None]
    sky[:, :, 2] += 1.3 * dust_a * fade[:, None]

    sky = np.clip(sky, 0, 255)
    img = Image.fromarray(sky.astype(np.uint8), "RGB").convert("RGBA")

    # --- Stars across full frame (density scales with resolution) ---
    area = W * H
    star_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(star_layer)

    # Dim point stars — sharp 1px, power-law magnitude
    n_dim = int(area / 2200)
    for _ in range(n_dim):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, H))
        mag = float(rng.random() ** 2.55)
        bright = int(35 + mag * 155)
        a = int(45 + mag * 165)
        sd.point((x, y), fill=(bright, bright + 2, min(255, bright + 20), a))

    # Mid stars — crisp small disks, tiny soft bloom only for brighter mid
    mid_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    md = ImageDraw.Draw(mid_layer)
    n_mid = max(120, int(area / 32000))
    for _ in range(n_mid):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, H))
        r = float(rng.uniform(0.55, 1.45))
        a = int(rng.integers(150, 240))
        md.ellipse([x - r, y - r, x + r, y + r], fill=(215, 222, 255, a))
    mid_soft = mid_layer.filter(ImageFilter.GaussianBlur(radius=0.55))

    # Bright stars — soft diffraction spikes (parallax-ready focal points)
    bright_core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bright_spikes = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bc = ImageDraw.Draw(bright_core)
    bs = ImageDraw.Draw(bright_spikes)
    n_bright = max(28, int(area / 120000))
    for _ in range(n_bright):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, H))
        r = float(rng.uniform(1.05, 2.35))
        a = int(rng.integers(210, 255))
        bc.ellipse([x - r, y - r, x + r, y + r], fill=(238, 242, 255, a))
        spike = max(6, int(r * 5.5 + rng.uniform(2, 10)))
        col = (222, 230, 255, max(24, a // 6))
        bs.line([(x - spike, y), (x + spike, y)], fill=col, width=1)
        bs.line([(x, y - spike), (x, y + spike)], fill=col, width=1)
        if rng.random() < 0.35:
            d = int(spike * 0.55)
            bs.line([(x - d, y - d), (x + d, y + d)], fill=(210, 220, 255, a // 9), width=1)
            bs.line([(x - d, y + d), (x + d, y - d)], fill=(210, 220, 255, a // 9), width=1)

    spikes_soft = bright_spikes.filter(ImageFilter.GaussianBlur(radius=max(1.0, W / 2400)))
    core_soft = bright_core.filter(ImageFilter.GaussianBlur(radius=max(0.7, W / 3000)))
    core_crisp = bright_core.filter(ImageFilter.GaussianBlur(radius=0.30))

    out = Image.alpha_composite(img, star_layer)
    out = Image.alpha_composite(out, mid_soft)
    out = Image.alpha_composite(out, mid_layer)
    out = Image.alpha_composite(out, spikes_soft)
    out = Image.alpha_composite(out, core_soft)
    out = Image.alpha_composite(out, core_crisp)
    return out


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
    """Parallel bars + doubled crisp end dots; NO glow/halo; supersampled."""
    starts, ends, balls = bar_geometry()
    dx0 = ends[0][0] - starts[0][0]
    dy0 = ends[0][1] - starts[0][1]
    for s, e in zip(starts, ends):
        assert abs((e[0] - s[0]) - dx0) < 1e-9
        assert abs((e[1] - s[1]) - dy0) < 1e-9
    for i in range(1, len(starts)):
        assert abs((starts[i][0] - starts[i - 1][0]) - BAR_SPACING) < 1e-9
    assert BAR_SPACING > SVG_STROKE + 0.4, (BAR_SPACING, SVG_STROKE)
    assert all(abs(s[1] - START_Y) < 1e-9 for s in starts)
    assert all(abs(e[1] - END_Y) < 1e-9 for e in ends)

    S = max(1024, int(size * SUPERSAMPLE))
    S = min(S, 4096)
    png = cairosvg.svg2png(bytestring=mark_svg_bytes(starts, ends), output_width=S, output_height=S)
    bars = Image.open(io.BytesIO(png)).convert("RGBA")

    scale = S / 384.0
    r_dot = DOT_R * 12.0 * scale
    balls_px = [(u * 12.0 * scale, v * 12.0 * scale) for u, v in balls]

    pad_px = max(8, int(math.ceil(r_dot * 2.5)) + S // 128)
    canvas_s = S + 2 * pad_px
    bars_p = Image.new("RGBA", (canvas_s, canvas_s), (0, 0, 0, 0))
    bars_p.paste(bars, (pad_px, pad_px))

    ball_layer = Image.new("RGBA", (canvas_s, canvas_s), (0, 0, 0, 0))
    bd = ImageDraw.Draw(ball_layer)
    for cx, cy in balls_px:
        x, y = cx + pad_px, cy + pad_px
        # Flat crisp disk only — no rim/core split (reads as halo when downscaled)
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
    mark = draw_mark(max(side, 1024))
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
    floor_y = int(round(LAYOUT_FLOOR_RATIO * H))  # layout anchor only; no wet floor drawn
    return {"floor_y": floor_y, "mark": {"x": mx, "y": my, "w": mw, "h": mh}}


def compose(W: int, H: int, layout: dict, out_path: Path, seed: int = 22) -> None:
    m = layout["mark"]
    mx, my, mw, mh = int(m["x"]), int(m["y"]), int(m["w"]), int(m["h"])
    print(f"compose {W}x{H} mark=({mx},{my}) {mw}x{mh} -> {out_path.name}")

    base = make_starfield(W, H, seed=seed)
    mark = sized_mark(mw, mh)
    composed = base.copy()
    composed.alpha_composite(mark, (mx, my))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # PNG compress without palette dither
    composed.convert("RGB").save(out_path, optimize=True, compress_level=6)
    print(f"  wrote {out_path} ({out_path.stat().st_size} bytes)")


def main():
    with open(EXPORT_V17) as f:
        export = json.load(f)

    # Primary deliverables + theme primaries
    targets = [
        (3840, 2160, "okbay-wallpaper-16x9-v22.png", 22),
        (5120, 2160, "okbay-wallpaper-ultrawide-5120x2160-v22.png", 22),
        # Theme primaries (16x9 primary for omarchy.png / symlink target)
        (3840, 2160, "okbay-wallpaper-16x9.png", 22),
        (3840, 2160, "omarchy.png", 22),
        (5120, 2160, "okbay-wallpaper-ultrawide-5120x2160.png", 22),
        # Keep ultrawide primary as height-fit of same sky (guest often 3440×1440)
        (3440, 1440, "1-okbay-night.png", 22),
        (3440, 1440, "okbay-wallpaper-ultrawide-3440x1440.png", 22),
        (3440, 1440, "okbay-wallpaper-ultrawide.png", 22),
        (3440, 1440, "okbay-wallpaper-ultrawide-3440x1440-v22.png", 22),
    ]

    for W, H, name, seed in targets:
        layout = map_layout(W, H, export)
        compose(W, H, layout, OUT_DIR / name, seed=seed)

    # Scratch copies under /workspace
    for name in (
        "okbay-wallpaper-16x9-v22.png",
        "okbay-wallpaper-ultrawide-5120x2160-v22.png",
    ):
        src = OUT_DIR / name
        dst = SCRATCH / name
        dst.write_bytes(src.read_bytes())
        print(f"scratch {dst} ({dst.stat().st_size})")

    mark_ref = draw_mark(1024)
    mark_ref.save(OUT_DIR / "okbay-mark-faithful.png")
    print("wrote okbay-mark-faithful.png", mark_ref.size)
    print("done v22")


if __name__ == "__main__":
    main()
