# Okbay / Switchbay theme for Omarchy

- `colors.toml` — Switchbay chrome + CE doc-type palette
- `backgrounds/1-okbay-night.png` — **primary** wallpaper: ultrawide **3440×1440** (v19)
  - Near-**black** astronomical sky with Switchbay-palette nebula wisps (violet/cyan/green/orange/magenta)
  - Realistic star magnitudes (mostly tiny dim points; few bright with soft diffraction — no cartoon crosses)
  - **Native-res** wet black glass floor + procedural droplets; brand-color reflections in beads under the logo
  - Mark: five **parallel** bars with tightened spacing (~3.3 vs SVG 4), non-overlapping; white balls with **compact** soft radial glow + generous transparent pad (no clipped square halo)
- `backgrounds/okbay-wallpaper-ultrawide*.png` — 3440×1440 and 5120×2160 (v19)
- `backgrounds/okbay-wallpaper-*-v19.png` — explicit v19 copies
- `backgrounds/okbay-wallpaper-16x9.png` / `omarchy.png` — 1920×1080
- `backgrounds/okbay-wallpaper-square*.png` — 1280×1280
- `backgrounds/okbay-mark-faithful.png` / `okbay-mark-nobox.svg` — mark references (two terminals only; no boxed icon)
- Boxed `okbay-logo.svg` lives under `backgrounds/archive/` — do not use as wallpaper

Regenerate:

```sh
.venv/bin/python scripts/gen_wallpaper_v19.py
```

Apply:

```sh
omarchy theme set switchbay
omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/1-okbay-night.png
# or explicit ultrawide:
# omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/okbay-wallpaper-ultrawide-3440x1440.png
```
