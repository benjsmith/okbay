# Okbay / Switchbay theme for Omarchy

- `colors.toml` — Switchbay chrome + CE doc-type palette
- `backgrounds/1-okbay-night.png` — **primary** wallpaper: ultrawide **3440×1440** (v21)
  - **Photographic** wet-night plate (Milky Way sky + wet asphalt) full-frame
  - Plate upscaled with OpenCV **EDSR×2** (tiled) to 3840×2160, cached, then height-fit + mirror side pads (fallback: ESPCN / Lanczos+unsharp)
  - Mark: five **perfectly parallel** diagonal bars, flush tops/bottoms, tightened spacing (Δx≈3.35), supersampled ~4×
  - **Only two** tiny crisp silver/white end dots (outward nudge); **zero glow/halo** — never large grey orbs; never boxed icon frame
  - Wet **droplet** Switchbay color reflections under the logo on the photo floor
  - Optional very light grain only
- `backgrounds/okbay-wallpaper-ultrawide*.png` — 3440×1440 and 5120×2160 (v21)
- `backgrounds/okbay-wallpaper-*-v21.png` — explicit v21 copies
- `backgrounds/archive/bg-source-16x9.png` — photographic plate source (1920×1080)
- `backgrounds/archive/bg-source-16x9-edsr2x.png` — cached EDSR×2 upscaled plate (3840×2160)
- `backgrounds/okbay-wallpaper-16x9.png` / `omarchy.png` — 1920×1080
- `backgrounds/okbay-wallpaper-square*.png` — 1280×1280
- `backgrounds/okbay-mark-faithful.png` / `okbay-mark-nobox.svg` — mark references (two terminals only; no boxed icon)
- Boxed `okbay-logo.svg` lives under `backgrounds/archive/` — do not use as wallpaper

Regenerate:

```sh
.venv/bin/python scripts/gen_wallpaper_v21.py
```

Apply:

```sh
omarchy theme set switchbay
omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/1-okbay-night.png
# or explicit ultrawide:
# omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/okbay-wallpaper-ultrawide-3440x1440.png
```
