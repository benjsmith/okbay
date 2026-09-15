# Atlas host — option-3 frameless packaging

OKBay Atlas runs as a **frameless Chromium app window** on Omarchy (option 3),
not inside Quickshell WebEngine (option 1 — frozen) or a native QML scene
(option 2 — later).

## Launcher

`contrib/okbay-open-atlas.sh` (bound to **Super+Shift+K** via
`contrib/hypr-bindings.lua`):

1. Focus an existing Atlas Chromium if present (class `OkbayAtlas` or URL
   `8766/atlas`).
2. Otherwise launch once:
   `chromium --ozone-platform=wayland --class=OkbayAtlas --app=http://127.0.0.1:8766/atlas --start-fullscreen`
3. Does **not** call `omarchy-shell summon` by default (`OKBAY_DO_SUMMON=1` only
   for menu/plugin paths) — summon + Chromium raced and opened two windows.

Override URL/class with `OKBAY_ATLAS_URL` / `OKBAY_ATLAS_CLASS`.

## Hyprland windowrules

See the comment block at the bottom of `contrib/hypr-bindings.lua`. Typical:

```
windowrulev2 = float, class:^(OkbayAtlas)$
windowrulev2 = fullscreen, class:^(OkbayAtlas)$
# optional:
# windowrulev2 = workspace special:okbay, class:^(OkbayAtlas)$
```

## Serve + views

- Python daemon: `okbay serve` / `okbayd` on `:8766`
- Stem index warms at serve start (daemon thread) so modal page opens stay fast
  after the first warm, including on 9p-mounted Biocure wikis
- Host UI is a **views shell**: Atlas is one view among Viewer / Table / Library /
  Projects / Reviews (+ dynamic HTML decks). See `docs/VIEWS.md`.

## Smoke (Omarchy guest)

```bash
okbay serve   # or systemctl --user start okbayd
# wait for /health
curl -s http://127.0.0.1:8766/health
# Super+Shift+K → one fullscreen Chromium; repeat → focus, not second window
# Click a graph node → modal <<1s after warm (check okbayd log / stem-index.json)
```
