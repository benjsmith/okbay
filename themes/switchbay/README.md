# Okbay / Switchbay theme for Omarchy

- `colors.toml` — Switchbay chrome + CE doc-type palette
- `foot.ini` — Foot terminal colors (from `colors.toml` + Omarchy `foot.ini.tpl`); ship so Omarchy theme include works without waiting on `omarchy-theme-set`
- `backgrounds/1-okbay-night.png` — **primary** wallpaper: ultrawide **3440×1440** (v22)
  - **Starfield-only** deep night sky (procedural) — **no** wet surface / nanotexture glass plate
  - Sharp magnitude-distributed stars + soft diffraction on bright points; subtle palette nebula depth
  - Mark: five **perfectly parallel** diagonal bars, flush tops/bottoms, tightened spacing (Δx≈3.35), supersampled ~4×
  - **Only two** silver/white end dots — BL nudged left, TR nudged right; **2× v21 size** (DOT_R 0.80); crisp flat disks, **zero glow/halo**; never boxed icon frame
- `backgrounds/okbay-wallpaper-16x9-v22.png` — **3840×2160** primary 16×9
- `backgrounds/okbay-wallpaper-ultrawide-5120x2160-v22.png` — **5120×2160**
- `backgrounds/okbay-wallpaper-*-v22.png` — explicit v22 copies
- `backgrounds/okbay-wallpaper-16x9.png` / `omarchy.png` — 3840×2160 (same as v22)
- `backgrounds/okbay-wallpaper-ultrawide*.png` — 3440×1440 and 5120×2160 (v22)
- `backgrounds/okbay-mark-faithful.png` / `okbay-mark-nobox.svg` — mark references (two terminals only; no boxed icon)
- Boxed `okbay-logo.svg` lives under `backgrounds/archive/` — do not use as wallpaper
- Photographic plate archives (`archive/bg-source-*.png`) retained for history; **not** used by v22

Regenerate:

```sh
.venv/bin/python scripts/gen_wallpaper_v22.py
```

Apply:

```sh
omarchy theme set switchbay
omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/1-okbay-night.png
# or 16×9 / ultrawide:
# omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/okbay-wallpaper-16x9-v22.png
# omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/okbay-wallpaper-ultrawide-5120x2160-v22.png
```

## Regenerate foot.ini

Omarchy normally renders `default/themed/foot.ini.tpl` when you `omarchy theme set switchbay`.
This repo ships a pre-resolved `foot.ini` so Foot’s theme include works even before a theme refresh.

```sh
# On an Omarchy guest with OMARCHY_PATH set:
omarchy-theme-set switchbay   # regenerates ~/.local/state/omarchy/current/theme/foot.ini
cp ~/.local/state/omarchy/current/theme/foot.ini themes/switchbay/foot.ini
```
