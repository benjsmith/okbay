# Okbay e2e handover (Omarchy VM / Grok-bot with a screen)

> Status as of 2026-09-10. README still says **under construction**. That is
> correct. This file is only for a later session that *can* sit on a real
> Omarchy desktop and tick the boxes this build environment could not.

This repo was built on a headless 2 GiB container: no `omarchy` CLI, no
Hyprland, no Quickshell, no qemu. HTTP + Python unit tests passed. **Nothing
here has been seen on a live Omarchy shell.** That is the job of the next
session.

## Handover now?

**Yes, for desktop e2e. No, for a release.**

Hand over when the next box has:

- Omarchy (Quattro-era plugin contract: `manifest.json` + QML kinds)
- A real session: Hyprland + Quickshell + a display (“brush screen”)
- Network + `cargo`/`python3`/`systemctl --user`
- Ability to install a third-party plugin and a user theme

Do **not** remove the README banner, do **not** `omarchy plugin add` for
end users, do **not** point the vault at files you care about, until the
checklist below is green on that machine.

The rest of the plugin (QML, rust okbayd, Python CLI, tests, Switchbay theme)
lives in this same repository. If you only see six files, `git pull`.

## Screen checklist lives below after install.

## What is already built

| Piece | Path | Notes |
|---|---|---|
| Plugin id | `benjsmith.okbay` | kinds: service, bar-widget, overlay, panel |
| QML | `BarWidget.qml` `Overlay.qml` `Panel.qml` `Service.qml` `Model.js` | Overlay/Panel talk HTTP |
| Rust daemon | `crates/okbayd` | std HTTP on **127.0.0.1:8766** |
| Python CLI | `src/okbay` | ingest, wiki, reviews, desks, MCP |
| Theme pack | `themes/switchbay/` | colors.toml + mark wallpaper |
| Installer | `contrib/setup.sh` | |
| Tests | `tests/test_okbay.py` `tests/test_e2e_http.py` | headless |

Port **8766**. Workspace `~/Work/okbay/{vault,wiki}`.
Status: `~/.local/state/okbay/status.json`.
Reviews ledger: `~/Work/okbay/.okbay/reviews.json`.

## Install on the Omarchy VM (dev only)

```sh
cd /path/to/okbay
PYTHONPATH=src python3 -m pytest tests/test_okbay.py tests/test_e2e_http.py -q
bash contrib/setup.sh
omarchy plugin add /path/to/okbay --enable
omarchy theme set switchbay
systemctl --user status okbayd.service
curl -s http://127.0.0.1:8766/health
```

If plugin add refuses a local path:

```sh
ln -sfn /path/to/okbay ~/.config/omarchy/plugins/benjsmith.okbay
omarchy plugin enable benjsmith.okbay
```

## Screen checklist

### A. Bar widget
- [ ] Chip visible after enable + shell restart
- [ ] SETUP until setup.sh has run; then page count or desk name
- [ ] Left click Atlas, right click Reviews

### B. Atlas overlay
- [ ] Search hits `:8766/api/search` (no okbay process flicker)
- [ ] Nodes colored by wiki kind from `/api/theme`
- [ ] Changing Omarchy theme changes node colors; Switchbay uses CE type palette
- [ ] Focused edges use accent, not a hardcoded blue

### C. Reviews + desks
- [ ] Accept writes wiki page; Reject does not
- [ ] Desk buttons update status.json desk.id

### D. Knowledge loop
```sh
echo "The landlord requires two months deposit." > /tmp/lease.txt
okbay ingest /tmp/lease.txt
okbay search deposit --json
okbay propose --title "Deposit rule" --body "Two months deposit." --kind fact
okbay review accept 1
```

### E. Theme pack
- [ ] `omarchy theme set switchbay` applies mint-on-charcoal + mark wallpaper

### F. Safety
- [ ] Daemon binds 127.0.0.1 only
- [ ] README banner still present

## Known holes

No JIT tabs. Atlas may be a browser fallback. Rust crate is std HTTP only.
Cargo target dir on noexec mounts: `CARGO_TARGET_DIR=$HOME/.cache/okbay/target`.

When A-E are green on a live Omarchy session, the next change may remove the README banner. Not before.

## Testing feedback todo

Session follow-ups: [TESTING-FEEDBACK-TODO.md](TESTING-FEEDBACK-TODO.md).
