# Okbay / Switchbay theme for Omarchy

- `colors.toml` — Switchbay chrome + CE doc-type palette
- `backgrounds/1-okbay-night.png` — **primary** wallpaper: ultrawide **3440×1440** (v18)
  - Native procedural night sky (gradient + starfield + nebula) — not an upscaled 1280×720 plate
  - Wet-floor band optionally taken from the old BG below `floor_y` only
  - Mark: five **parallel** SVG bars (identical Δx/Δy), thin enough not to overlap; white balls with **soft radial glow** only (no hard concentric shells)
- `backgrounds/okbay-wallpaper-ultrawide*.png` — 3440×1440 and 5120×2160 (v18)
- `backgrounds/okbay-wallpaper-*-v18.png` — explicit v18 copies
- `backgrounds/okbay-wallpaper-16x9.png` / `omarchy.png` — 1920×1080
- `backgrounds/okbay-wallpaper-square*.png` — 1280×1280
- `backgrounds/okbay-mark-faithful.png` / `okbay-mark-nobox.svg` — mark references (two terminals only; no boxed icon)
- Boxed `okbay-logo.svg` lives under `backgrounds/archive/` — do not use as wallpaper

Regenerate:

```sh
.venv/bin/python scripts/gen_wallpaper_v18.py
```

Apply:

```sh
omarchy theme set switchbay
omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/1-okbay-night.png
# or explicit ultrawide:
# omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/okbay-wallpaper-ultrawide-3440x1440.png
```
