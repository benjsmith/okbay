# Switchbay theme for Omarchy

Optional desktop theme that ships with okbay. Not required for the plugin.

- `colors.toml` — Switchbay chrome + CE doc-type palette mapped onto Omarchy keys
- `backgrounds/switchbay-mark.svg` — constellation mark on `#0f1115` (source of truth)
- Raster wallpapers (`switchbay-icon.png`, `preview.png`) are generated from that SVG and are not stored in git.

Install (when okbay is actually released):

```
mkdir -p ~/.config/omarchy/themes
cp -a themes/switchbay ~/.config/omarchy/themes/switchbay
omarchy theme set switchbay
```

Until the okbay README banner comes down, treat this as a draft palette, not a published Omarchy extra.
