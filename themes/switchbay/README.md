# Okbay / Switchbay theme for Omarchy

- `colors.toml` — Switchbay chrome + CE doc-type palette
- `backgrounds/1-okbay-night.png` — **primary** wallpaper: ultrawide **3440×1440** (v20)
  - **Photographic** wet-night plate (Milky Way sky + wet asphalt) full-frame — Lanczos upscaled; no procedural sky/stars
  - Ultrawide: height-fit + mirrored side pads (no stretch; sky/floor preserved)
  - Mark: five **SVG-faithful** parallel bars (spacing Δx=4), supersampled ~4× then Lanczos down for smooth edges
  - White balls with **soft radial glow** (smaller than v18 rings) + extra transparent pad (no clipped halo); crisp white cores
  - Wet **droplet** Switchbay color reflections under the logo (v17 spirit) on the photo floor
  - Optional very light grain only
- `backgrounds/okbay-wallpaper-ultrawide*.png` — 3440×1440 and 5120×2160 (v20)
- `backgrounds/okbay-wallpaper-*-v20.png` — explicit v20 copies
- `backgrounds/archive/bg-source-16x9.png` — photographic plate source (1920×1080)
- `backgrounds/okbay-wallpaper-16x9.png` / `omarchy.png` — 1920×1080
- `backgrounds/okbay-wallpaper-square*.png` — 1280×1280
- `backgrounds/okbay-mark-faithful.png` / `okbay-mark-nobox.svg` — mark references (two terminals only; no boxed icon)
- Boxed `okbay-logo.svg` lives under `backgrounds/archive/` — do not use as wallpaper

Regenerate:

```sh
.venv/bin/python scripts/gen_wallpaper_v20.py
```

Apply:

```sh
omarchy theme set switchbay
omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/1-okbay-night.png
# or explicit ultrawide:
# omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/okbay-wallpaper-ultrawide-3440x1440.png
```
