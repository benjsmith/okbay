# Changelog

## Unreleased

**Breaking:** Super+Shift+K now opens the full product on its own workspace
instead of the Atlas window alone, and `okbay serve` now starts okstratr.
Wallpapers are replaced by the v22 set under the same file names.

- **Super+Shift+K opens the full product.** It switches to an empty Hyprland
  workspace and lays out four windows in a 2x2 grid: Atlas top left, Nautilus
  (on the workspace's wiki) top right, Herdr bottom left, and the okstratr
  panel bottom right. Super+Ctrl+K does the same on a Mac host that captures
  Super+Shift+K. Atlas alone is still `contrib/okbay-open-atlas.sh`; rebind
  Super+Shift+K to it in `~/.config/hypr/bindings.lua` to keep the old
  behaviour. The opener uses `OKBAY_WORKSPACE`, or the workspace okbay last
  served; `OKBAY_SRC` and `OKSTRATR_SRC` point it at source checkouts when the
  CLIs aren't installed. Herdr agents are never started inside the okbay
  source checkout.
- **okbay starts okstratr.** `okbay serve` starts `okstratr serve` on `:8767`
  and restarts it if it stops. Set `OKBAY_AUTOSTART_OKSTRATR=0` to turn this
  off. `okbay core-skills status|ensure` and `GET /api/core-skills/status`
  report CE and okstratr health.
- **HTML or QML viewer, not both.** `okbay viewer status|set html|qml` and
  `GET/POST /api/viewer` choose the viewer. In QML mode the HTML pages (`/`,
  `/atlas`, `/views/*`) return 409 and the QML panels don't open Chromium; the
  JSON API keeps working. The default stays `html`.
- **okstratr harness settings from okbay.** `okbay harness
  list|enable|disable|set|reload` and `/api/okstratr/harness*` read and edit
  okstratr's harness list; okbay keeps no list of its own.
- **okstratr notifications go to Herdr.** `POST /api/okstratr/host-notify` and
  `okbay host-notify` append okstratr notifications to
  `~/.local/state/okbay/herdr-notify.jsonl`.
- **Wallpaper v22**: a starfield background with a sharper logo.

- **Viewer source body**: `GET /api/atlas/source` (vault path sandbox) + views-shell renders source HTML; wiki↔source history preserved.
- **Bar / menu**: left-click Atlas launcher; right-click Library `#view=library`; menu Library entry.
- **Hypr OkbayAtlas**: `contrib/okbay-atlas.conf` + `install-okbay-atlas-rules.sh` / setup.sh → `hyprctl reload`.
- **Stem index warm**: `wiki.warm_stem_index()` / background warm at `serve` start; invalidate+rewarm on workspace switch; optional `.okbay/stem-index.json` persist for faster 9p restarts. Atlas modal cold-open no longer rebuilds the index on every click after warm.
- **Frameless Atlas packaging**: `okbay-open-atlas.sh` uses `--class=OkbayAtlas`; Hyprland windowrule notes in `contrib/hypr-bindings.lua`; `docs/ATLAS-HOST.md`.
- **Views shell**: bottom `view:` control is a views popup (Atlas / Viewer / Table / Library / Projects / Reviews + dynamic). Viewer sticky selection + back/forward; `GET|POST|DELETE /api/views`, sandboxed `/views/<id>`; MCP `okbay_list_views` / `okbay_publish_view` / `okbay_open_view`; `docs/VIEWS.md`, `skills/okbay-views`.


- Wallpaper **v21**: EDSR×2 upscaled photographic wet-night plate (cached 3840×2160); tightened flush parallel bars (Δx≈3.35); **tiny crisp** silver end dots with outward nudge and **zero glow/halo** (no large grey orbs); droplet Switchbay reflections on photo floor.

- Atlas **chrome parity** (Switchbay/CE): ingest **+** (`i`), workspace switcher (`o` + `/api/workspace/list|use|add`), edge mode auto/on/off (`e` + vendor `setEdges`), views popup (`v`; Atlas/Viewer/Table/…; classic via `?viewer=classic`), minimap toggle (`m`), in-chrome help (`?`). Vendored KnowledgeAtlas bump (setEdges) + `d3.min.js` / `classic-graph.js`.

- Wallpaper **v20**: photographic wet-night plate full-frame (Lanczos upscale to 3440×1440 / 5120×2160; ultrawide height-fit + mirror side pads); SVG-faithful bar spacing (Δx=4) with ~4× supersample; smaller soft ball glow + transparent pad + crisp cores; v17-style droplet color reflections on the photo floor (no procedural sky/floor).
- Atlas **Super+Shift+K** reopen: `okbay-open-atlas.sh` always focuses/launches Chromium (uwsm-app / Wayland); summon is best-effort only and no longer short-circuits when the plugin is already loaded. Soften Panel/Overlay `openAtlasWindow` (delegate to helper; no blanket `pkill`).

- Wallpaper **v19**: tighter bar spacing (~3.3); smaller ball glow + pad (no clipped halo); near-black sky + Switchbay-palette nebulae; realistic stars; native wet black glass floor with procedural droplets + brand-color reflections (old plate grit optional only).
- Wallpaper **v18**: native 3440×1440 / 5120×2160 night sky (procedural stars + nebula); wet floor from old BG only below floor_y; mark bars parallel + non-overlapping; soft radial ball glow (no hard shells).
- Atlas **Super+Shift+K**: `contrib/okbay-open-atlas.sh` exports `OMARCHY_PATH`, summons atlas, Chromium fallback; `setup.sh` installs script + merges Hypr bind. Note: Omarchy **Super+Shift+O** is Obsidian (Okstratr may override).


## 0.1.1 — 2026-09-12

- Work coverage defaults (`~/Work` / `OKBAY_WORK_ROOT`); Biocure as active demo hub (not opt-in).
- Optional focused workspaces via `okbay workspace split` (watch_roots + default `opt_out`).
- Pre-ingest privacy gate (curiosity-merge GDPR wrap + financial heuristics) with `needs_confirm`.
- Efficient watcher (watchdog or mtime index + debounce); code repos → decision notes only.
- Docs: `docs/WORK-COVERAGE.md`; CLI `coverage` / `workspace` / `watch`; HTTP privacy scan, ingest confirm, `POST /api/workspace/split`.

## 0.1.0 — 2026-09-10

- First cut of the Omarchy plugin: QML surfaces + okbayd + CLI + MCP + three skills.
- Workspace `~/Work/okbay`, port 8766, propose→review gate, Atlas overlay, standing desks.

- Omarchy 0.56: float action=set tiles floating windows; arrange uses toggle-only + proven 2x2 recipe (live green on Mac Mini).
