"""v17: mark + wet-floor droplet reflections only — no okbay text.

Placement from wallpaper-playground/export.json (16x9 + square_mapped).
Ignores glow_scale and all text fields. Does not write themes/switchbay/backgrounds/.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageChops
import json
import os

BG = "/home/box/sand-data/agents/4deed81b-eba7-47c9-8fb0-f1684b45907d/assets/3e1bdcc8217b2106b1622c911a441c95dc2204d5eedf02ca91e21324dabaaf26.png"
EXPORT = "/workspace/wallpaper-playground/export.json"
OUT_W = "/workspace/okbay-wallpaper-16x9-v17.png"
OUT_SQ = "/workspace/okbay-wallpaper-square-v17.png"

colors = ['#5a2bf0', '#2079ab', '#12996a', '#f08a12', '#a83e7e']
FLOOR_RATIO = 0.715  # kept for parity; floor_y comes from export


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def crop_alpha(img, pad=2):
    a = img.split()[-1]
    bbox = a.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    return img.crop((max(0, l - pad), max(0, t - pad), min(img.size[0], r + pad), min(img.size[1], b + pad)))


def draw_mark(size, stroke_scale=1.28):
    S = 32.0
    pad = size * 0.08
    scale = (size - 2 * pad) / S
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def xy(u, v):
        return pad + u * scale, pad + v * scale

    sw = max(2, int(3.2 * scale * stroke_scale))
    starts = [(5, 27), (9, 27), (13, 27), (17, 27), (21, 27)]
    ends = [(11, 7), (15, 7), (19, 7), (23, 7), (27, 7)]
    for (x1, y1), (x2, y2), c in zip(starts, ends, colors):
        col = hex_rgb(c) + (255,)
        d.line([xy(x1, y1), xy(x2, y2)], fill=col, width=sw)
        r = sw // 2
        for pt in (xy(x1, y1), xy(x2, y2)):
            d.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=col)
    r_dot = int(2.35 * scale)
    px_nudge = max(4, int(6 * size / 512))
    for (cu, cv), dx in (((4, 28), -px_nudge), ((28, 4), +px_nudge)):
        x, y = xy(cu, cv)
        x += dx
        for gr, ga in ((int(r_dot * 1.8), 55), (int(r_dot * 1.35), 130)):
            d.ellipse([x - gr, y - gr, x + gr, y + gr], fill=(215, 219, 226, ga))
        d.ellipse([x - r_dot, y - r_dot, x + r_dot, y + r_dot], fill=(215, 219, 226, 255))
        hr = max(2, r_dot // 3)
        d.ellipse(
            [x - r_dot // 2 - hr // 2, y - r_dot // 2 - hr // 2,
             x - r_dot // 2 + hr // 2, y - r_dot // 2 + hr // 2],
            fill=(255, 255, 255, 210),
        )
    glow = img.filter(ImageFilter.GaussianBlur(radius=max(3, size // 70)))
    out = Image.alpha_composite(Image.new('RGBA', (size, size), (0, 0, 0, 0)), glow)
    out = Image.alpha_composite(out, img)
    return crop_alpha(out, pad=max(4, size // 64))


def droplet_mask(bg_rgba, floor_y):
    W, H = bg_rgba.size
    floor = bg_rgba.crop((0, floor_y, W, H)).convert('L')
    hi = ImageOps.autocontrast(floor)
    detail = ImageChops.subtract(hi, hi.filter(ImageFilter.GaussianBlur(3)))
    beads = detail.point(lambda p: 255 if p > 14 else (int(p * 12) if p > 6 else 0))
    beads = beads.filter(ImageFilter.GaussianBlur(0.4))
    mask = Image.new('L', (W, H), 0)
    mask.paste(beads, (0, floor_y))
    return mask


def color_ramp_image(W, H, x0, x1, floor_y, reach):
    cols = [hex_rgb(c) for c in colors]
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    px = img.load()
    span = max(1, x1 - x0)
    for y in range(floor_y, min(H, reach)):
        t = (y - floor_y) / max(1, reach - floor_y)
        fade = int(255 * ((1 - t) ** 0.85))
        for x in range(max(0, x0), min(W, x1)):
            u = (x - x0) / span
            i = min(len(cols) - 1, int(u * len(cols)))
            f = u * len(cols) - i
            c0 = cols[i]
            c1 = cols[min(len(cols) - 1, i + 1)]
            r = int(c0[0] * (1 - f) + c1[0] * f)
            g = int(c0[1] * (1 - f) + c1[1] * f)
            b = int(c0[2] * (1 - f) + c1[2] * f)
            px[x, y] = (r, g, b, fade)
    return img


def droplet_reflections(base, mark_xy, mark_size, text_xy, text_size, floor_y):
    """Floor-only wet-bead color bleed (v9 approved spirit / v13 implementation)."""
    W, H = base.size
    beads = droplet_mask(base, floor_y)
    mx, my = mark_xy
    mw, mh = mark_size
    tx, ty = text_xy
    tw, th = text_size
    x0 = min(mx, tx) - int(mw * 0.05)
    x1 = max(mx + mw, tx + tw) + int(mw * 0.05)
    cx = (x0 + x1) // 2
    reach = min(H, floor_y + int(H * 0.32))
    fall = Image.new('L', (W, H), 0)
    fd = ImageDraw.Draw(fall)
    half = max(20, (x1 - x0) // 2)
    for y in range(floor_y, reach):
        t = (y - floor_y) / max(1, reach - floor_y)
        row = int(255 * ((1 - t) ** 0.7))
        h = int(half * (0.55 + 0.45 * (1 - t)))
        for x in range(max(0, cx - h), min(W, cx + h)):
            dx = abs(x - cx) / max(1, h)
            a = int(row * ((1 - dx * dx) ** 1.5))
            if a:
                fd.point((x, y), fill=max(fall.getpixel((x, y)), a))
    fall = fall.filter(ImageFilter.GaussianBlur(7))
    fall.paste(0, (0, 0, W, floor_y))

    ramp = color_ramp_image(W, H, x0, x1, floor_y, reach)
    bead_gate = ImageChops.multiply(beads, fall)

    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    r, g, b, a = ramp.split()
    a = ImageChops.multiply(a, bead_gate)
    hot = beads.point(lambda p: min(255, int(p * 1.4)) if p > 40 else 0)
    hot = ImageChops.multiply(hot, fall)
    a2 = ImageChops.lighter(a, ImageChops.multiply(a.point(lambda p: min(255, int(p * 1.6))), hot))
    tint = Image.merge('RGBA', (r, g, b, a2))
    tint = tint.filter(ImageFilter.GaussianBlur(0.6))
    layer = Image.alpha_composite(layer, tint)

    glint = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glint)
    for gx in (mx + int(mw * 0.12), mx + int(mw * 0.88)):
        for yy in range(floor_y, min(H, floor_y + int(H * 0.18)), 3):
            gd.ellipse([gx - 2, yy - 1, gx + 2, yy + 3], fill=(220, 225, 235, 90))
    glint = glint.filter(ImageFilter.GaussianBlur(1.2))
    layer = Image.alpha_composite(
        layer,
        Image.merge('RGBA', (*glint.split()[:3], ImageChops.multiply(glint.split()[3], bead_gate))),
    )

    layer.paste(Image.new('RGBA', (W, floor_y), (0, 0, 0, 0)), (0, 0))
    return Image.alpha_composite(base.convert('RGBA'), layer)


def sized_mark(w, h):
    """Draw mark at max(w,h) then LANCZOS-resize to exact export w×h."""
    side = max(w, h)
    mark = draw_mark(side)
    if mark.size != (w, h):
        mark = mark.resize((w, h), Image.Resampling.LANCZOS)
    return mark


def compose_from_export(key, out_path, export):
    cfg = export[key]
    W = cfg['canvas']['w']
    H = cfg['canvas']['h']
    floor_y = int(cfg['floor_y'])
    m = cfg['mark']
    mx, my = int(m['x']), int(m['y'])
    mw, mh = int(m['w']), int(m['h'])
    # reflection dy/intensity from export (dy=0, intensity=1 — no offset applied)
    # Ignored: glow_scale, text fields

    print(f'{key}: canvas={W}x{H} floor_y={floor_y} mark=({mx},{my}) size={mw}x{mh}')
    print(f'  text omitted; reflection dummy centered on mark')

    bg = Image.open(BG).convert('RGBA').resize((W, H), Image.Resampling.LANCZOS)
    mark = sized_mark(mw, mh)

    # Dummy text box mark-aligned so color ramp centers under logo (no glyphs drawn)
    text_xy = (mx, my)
    text_size = (mw, mh)

    composed = droplet_reflections(bg, (mx, my), mark.size, text_xy, text_size, floor_y)
    composed.alpha_composite(mark, (mx, my))
    composed.convert('RGB').save(out_path)
    print(f'wrote {out_path} ({os.path.getsize(out_path)} bytes)')
    return (mx, my, mw, mh, floor_y)


def main():
    with open(EXPORT) as f:
        export = json.load(f)

    assert os.path.exists(BG), f'missing BG: {BG}'

    p16 = compose_from_export('16x9', OUT_W, export)
    psq = compose_from_export('square_mapped', OUT_SQ, export)

    for path in (OUT_W, OUT_SQ):
        assert os.path.exists(path), path
        sz = os.path.getsize(path)
        assert sz > 100_000, f'{path} too small: {sz}'
        im = Image.open(path)
        print(f'verify {path}: mode={im.mode} size={im.size} bytes={sz}')

    print('TEXT OMITTED: no draw_okbay_text / no text layer composited')
    print('done')
    print('mark_16x9', p16)
    print('mark_square', psq)


if __name__ == '__main__':
    main()
