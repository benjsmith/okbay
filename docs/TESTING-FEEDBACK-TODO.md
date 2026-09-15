# Okbay testing feedback — todo

Captured from the 2026-09-10/11 Omarchy VM e2e session (Grok Bot Okbay Tester).
Update checkboxes as items land. Do **not** lift the README under-construction banner until the original `E2E-HANDOVER.md` A–E screen checklist is green on a responsive Omarchy session.

## Done in that session

- [x] Install Omarchy 4.0.3 in QEMU (TCG; nested KVM broken on the host box)
- [x] `contrib/setup.sh` + rust `okbayd`; `/health` ok
- [x] Enable plugin `benjsmith.okbay` (service, bar-widget, overlay, panel)
- [x] Headless pytest (`test_okbay.py`, `test_e2e_http.py`) — 5 passed
- [x] Knowledge loop D: ingest → search → propose → review accept
- [x] Copy full Biocure wiki/vault into `~/Work/okbay` and rebuild graph  
      (~40,097 nodes / ~180k edges / 39,122 pages)
- [x] Switchbay wallpaper **v9** approved: night sky + wet glass; under-text glow masked to wet beads/pools; terminal balls nudged outward; no boxed icon; no colored sky droplets  
      Primary theme files: `themes/switchbay/backgrounds/1-okbay-night.png`, `omarchy.png`

## Open — product / UX

### Atlas surface (CE parity via option 3)

Strategy locked 2026-09-11: **freeze option 1** (Quickshell + Qt WebEngine — crashes on this guest).
Ship **CE Atlas viewer parity** hosted as **option 3** (frameless Chromium `--app=` / Hyprland kiosk).
Native QML (option 2) only after CE parity.

Minimum = CE look/feel/performance: log-space shells/border, fast Fuse search, wiki + source browsers, file highlighting.
Stretch = Omarchy uplifts (Switchbay theme, bar summon, `okbay locate`, optional native file browser).

- [x] CE Atlas audit → `docs/CE-ATLAS-PARITY-AUDIT.md` (knowledge-atlas + wiki-view + data contract)
- [x] Okbayd data bridge: `GET /api/atlas/data` → CEData (`atlas_ce` Py+Rust); see `CE-ATLAS-PARITY-AUDIT.md` §7 Slice 0
- [x] Parity A — canvas mount: KnowledgeAtlas hybrid + **CE Policy A** (`maxAggregates:0`, `coreCapacity=corpusSize`); vendor JS on `/atlas` (2026-09-11 aggregate/minimap fix; Biocure visual confirm via screenshot)
- [x] Parity B — chrome: Fuse search, slim wiki/source modal, in-atlas focus (`atlas-chrome.js`; see audit §7 Slice 2)
- [x] Option 3 packaging: frameless Chromium `--class=OkbayAtlas` + Hypr notes (`docs/ATLAS-HOST.md`); bar left-click still TBD
- [x] File highlight via `okbay locate` — modal **Reveal files**, resolve-only on open (`reveal=0`), toast + sources/files list
- [x] Omarchy-native file browser reveal — prefer Nautilus (`uwsm-app` → `nautilus --select` / `--new-window`), fall back to `xdg-open` (see note below)
- [x] Label option buttons + type popup (CE `initAtlasControls` slim port in atlas chrome)
- [x] Label/type controls **visibly** mounted bottom-left after KnowledgeAtlas.mount (was top-right low-contrast; screenshots missed them)
- [x] Sidebar expand/collapse-all (CE `sidebar-toggle-all` chevron)
- [x] Fuse search → graph highlight via `engine.select` + `engine.focus` (typing + row select)
- [x] Classic graph chooser gated: `MIN_ATLAS_PAGES≈360` — Biocure Atlas-only; `#viewer-mode` stays hidden
- [ ] Confirm bar chip visually: left-click Atlas, right-click Reviews
- [ ] Later only: native QML Scene Graph if kiosk still feels non-Omarchy
- [x] Interim: Chromium `--app=/atlas` opener (now CE KnowledgeAtlas host; SVG circle removed)
- [x] Slice 1: vendor `knowledge-atlas.js` + mount against `/api/atlas/data` (see `CE-ATLAS-PARITY-AUDIT.md` §7)
- [x] Slice 2: Fuse sidebar + slim wiki modal + focus/locate (`atlas-chrome.js`, `GET /api/atlas/page`)
- [x] Slice 2+: type coloring (full palette), label/type controls, richer locate UX (2026-09-11)


#### How Reveal works on Omarchy

Omarchy’s default file browser is **Nautilus** (`org.gnome.Nautilus.desktop` for `inode/directory`; launchers `omarchy-launch-nautilus` / `omarchy-launch-nautilus-cwd` wrap `uwsm-app -- nautilus …`).

Atlas **Reveal files** → `GET /api/locate?stem=&reveal=1`:

1. Resolve wiki + vault/source paths (same as resolve-only `reveal=0`).
2. Prefer launching **Nautilus** so the file is highlighted:
   - existing file → `uwsm-app -- nautilus --select <path>` (else bare `nautilus --select`)
   - directory / missing file with existing parent → `nautilus --new-window <dir>`
3. Fall back to `xdg-open <parent>` when Nautilus is absent (non-Omarchy / headless).
4. Atlas modal status shows `via nautilus|xdg-open` or an error-styled `reveal failed: …` if launch fails.

Smoke: open Atlas, select a Biocure page with vault sources, click **Reveal files**; Nautilus should focus the source file. Headless CI keeps `reveal=0` / mocked spawn.

### Theme / wallpaper

- [ ] On a live Hyprland session, confirm `omarchy theme set switchbay` + `omarchy-theme-bg-set …/1-okbay-night.png` shows v9 (session was black/blank under TCG when last checked).
- [ ] Keep boxed `okbay-logo.svg` out of the active backgrounds set (archived under `backgrounds/archive/`).

### Graph / CE corpus fidelity

- [x] Map Curiosity Engine frontmatter `type:` → okbay `kind:` so Atlas node colors use the Switchbay CE palette
      (`wiki.parse` folds `type:`→kind; `okbay graph rebuild` / `enrich-kinds`; Rust theme full Switchbay palette).
- [ ] Verify edge semantics vs CE Kuzu graph (okbay builds from `[[wikilinks]]`; CE may count additional edge kinds).
- [ ] Atlas performance / pagination for full Biocure (~40k nodes) — `/graph` is a large JSON payload.

### Install / packaging

- [ ] Fix `contrib/setup.sh` okbay/okbayd wrappers: unquoted heredoc emptied `"$@"` at generate time (patched on the test guest under `~/.local/bin/`; upstream the fix).
- [ ] Document TCG vs KVM: nested KVM hit `kvm_spurious_fault` on the shared box; interactive desktop is slow under TCG.

### Handover checklist still open

Track against `docs/E2E-HANDOVER.md`:

- [ ] A — bar chip fully confirmed on a responsive session
- [ ] B — Atlas overlay (not browser): search, theme colors, focused edges
- [ ] C — Reviews + desks UI paths on shell surfaces
- [ ] E — Switchbay theme + v9 wallpaper visually confirmed
- [x] D — knowledge loop (CLI) passed
- [x] F — daemon binds 127.0.0.1; README banner kept

## Explicitly not yet

- Removing the README under-construction banner
- Declaring Atlas “beautiful fullscreen app” done (needs CE Atlas parity + option 3 packaging)
