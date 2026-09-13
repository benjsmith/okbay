# Changelog

## Unreleased

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
