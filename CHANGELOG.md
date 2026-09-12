# Changelog

## 0.1.1 — 2026-09-12

- Work coverage defaults (`~/Work` / `OKBAY_WORK_ROOT`); Biocure as active demo hub (not opt-in).
- Optional focused workspaces via `okbay workspace split` (watch_roots + default `opt_out`).
- Pre-ingest privacy gate (curiosity-merge GDPR wrap + financial heuristics) with `needs_confirm`.
- Efficient watcher (watchdog or mtime index + debounce); code repos → decision notes only.
- Docs: `docs/WORK-COVERAGE.md`; CLI `coverage` / `workspace` / `watch`; HTTP privacy scan, ingest confirm, `POST /api/workspace/split`.

## 0.1.0 — 2026-09-10

- First cut of the Omarchy plugin: QML surfaces + okbayd + CLI + MCP + three skills.
- Workspace `~/Work/okbay`, port 8766, propose→review gate, Atlas overlay, standing desks.
