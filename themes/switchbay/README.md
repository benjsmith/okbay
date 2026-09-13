# Okbay / Switchbay theme for Omarchy

- `colors.toml` — Switchbay chrome + CE doc-type palette
- `backgrounds/1-okbay-night.png` — **primary** wallpaper: ultrawide 3440×1440 (v17 logo-only) for wide / Try Omarchy guests
- `backgrounds/okbay-wallpaper-ultrawide*.png` — 3440×1440 and 5120×2160 variants
- `backgrounds/okbay-wallpaper-16x9.png` / `omarchy.png` — 1920×1080
- `backgrounds/okbay-wallpaper-square*.png` — 1280×1280 (phones / square previews)
- `backgrounds/okbay-mark-faithful.png` / `okbay-mark-nobox.svg` — mark references (two terminals only; no boxed icon)
- Boxed `okbay-logo.svg` lives under `backgrounds/archive/` — do not use as wallpaper

Apply:

```sh
omarchy theme set switchbay
omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/1-okbay-night.png
# or explicit ultrawide:
# omarchy-theme-bg-set ~/.config/omarchy/themes/switchbay/backgrounds/okbay-wallpaper-ultrawide-3440x1440.png
```
