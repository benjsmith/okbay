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

### Atlas surface (priority after wallpaper)

- [ ] **Ship fullscreen Quickshell overlay + embedded WebView** hosting `/atlas` (preferred near-term path). Overlay today is chrome-only and falls back to a Chromium window.
- [ ] Replace naive circle layout in `src/okbay/static/atlas.html` with a real force-directed (or better) graph renderer that stays usable at ~40k nodes (LOD / sampling / clustering as needed).
- [ ] Confirm bar chip visually: left-click Atlas, right-click Reviews; dismiss first-run toasts if they obscure the bar.
- [ ] Later: evaluate native QML Atlas if WebView feel is still wrong; kiosk Chromium only as stopgap.

### Theme / wallpaper

- [ ] On a live Hyprland session, confirm `omarchy theme set switchbay` + `omarchy-theme-bg-set …/1-okbay-night.png` shows v9 (session was black/blank under TCG when last checked).
- [ ] Keep boxed `okbay-logo.svg` out of the active backgrounds set (archived under `backgrounds/archive/`).

### Graph / CE corpus fidelity

- [ ] Map Curiosity Engine frontmatter `type:` → okbay `kind:` so Atlas node colors use the Switchbay CE palette (pages currently default to `note`).
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
- Declaring Atlas “beautiful fullscreen app” done (needs WebView overlay + renderer work)
