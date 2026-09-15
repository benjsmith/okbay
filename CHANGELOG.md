# Changelog

## Unreleased

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
