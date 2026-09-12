# Okbay

> **Under construction. Not ready to use.**
>
> This plugin is an early sketch, not a release. Do not install it. Do not
> run `omarchy plugin add`. Do not point it at real files. Do not treat the
> commands further down as a setup guide. Paths, APIs, and QML will change
> without notice.
>
> Come back when this banner is gone.

Desktop e2e for a later Grok session on a real Omarchy box: [docs/E2E-HANDOVER.md](docs/E2E-HANDOVER.md).

Work-root coverage, privacy gate, and watcher: **[docs/WORK-COVERAGE.md](docs/WORK-COVERAGE.md)**.

Compounding knowledge graph, Atlas overlay, and typed agent desks for [Omarchy](https://omarchy.org/).

Drop files. Do not organize them. Ask questions. The wiki gets stricter every time a proposed page survives review.

This is the v1 plugin designed after comparing [Switchbay](https://github.com/benjsmith/switchbay) with Omarchy. Switchbay is the existence proof. Okbay is the knowledge plane that rides Omarchy's existing agents, windows, skills, and plugin kinds — it does **not** wrap the Switchbay PWA.

Plugin id: `benjsmith.okbay`

## Name

`okbay` is not taken as a software product on PyPI, npm, or the Omarchy marketplace.

## What v1 is aiming at

- **Magical coverage of `~/Work`** (`OKBAY_WORK_ROOT`); hub vault/wiki at `~/Work/okbay`
- Biocure (and other corpora) as **named workspaces** via `okbay workspace use`
- Opt-out folders in `~/.config/okbay/coverage.toml`; privacy + financial pre-ingest gate
- Efficient `okbay watch` (watchdog or mtime index); code repos → decision notes only
- Workspace at `~/Work/okbay/{vault,wiki}` (Omarchy agents already start in `~/Work`)
- Ingest copies sources into the vault and extracts a `kind: source` wiki page with `extracted_from` provenance
- Agents **propose** wiki pages; you accept or reject in the Reviews panel. No blind writes.
- Atlas overlay searches nodes and can `okbay locate` the vault file / Hyprland window
- Standing desks `/curate` `/work` `/code` `/deck` are a tiny router + blackboard, not a bandit
- Skills land in the five roots Omarchy already maintains
- MCP server exposes the knowledge plane next to (not instead of) desktop MCP plugins
- HTTP on **127.0.0.1:8766** — never 8765

## Install on Omarchy

**Not yet.** There is no supported install. The commands below are notes for the people building it.

```sh
# do not run these until the banner at the top is gone
# omarchy plugin add https://github.com/benjsmith/okbay.git --enable
# git clone https://github.com/benjsmith/okbay
# cd okbay && bash contrib/setup.sh
```

`omarchy plugin add` never executes install hooks. That is intentional.

## Use

```sh
# okbay coverage status
# okbay workspace use biocure   # optional named corpus
# okbay watch once              # efficient Work-root pass
# okbay privacy ~/Work/notes/x.md && okbay ingest ~/Work/notes/x.md --confirm
# okbay ingest ~/Downloads/lease.pdf
# okbay ask "deposit rules"
# okbay desk start curate
# okbay reviews --json
# okbay review accept 1
# okbay locate deposit-rules
```

Bar widget (when this is actually shippable): left click opens Atlas, right click opens Reviews. SETUP appears until `okbay setup` has run.

## Layout

```
manifest.json          Omarchy plugin contract
BarWidget.qml          bar pulse
Overlay.qml            Atlas chrome
Panel.qml              Reviews + desks
Service.qml            headless keep-alive
src/okbay/             CLI, wiki, graph, reviews, desks, Python fallback HTTP
crates/okbayd          Rust warm daemon (preferred on :8766)
contrib/setup.sh       visible installer
contrib/okbayd.service systemd --user
contrib/mcp_server.py  stdio MCP
skills/                okbay-ask, okbay-curate, okbay-desk
themes/switchbay       optional Omarchy theme (doc-type palette + mark wallpaper)
```

## Testing

```sh
PYTHONPATH=src python3 -m pytest tests/test_okbay.py tests/test_work_coverage.py tests/test_e2e_http.py -q
```

Desktop e2e for a later Grok session on a real Omarchy VM: **[docs/E2E-HANDOVER.md](docs/E2E-HANDOVER.md)**.

## v1 is not

Power/Zen PWA, AG-UI, A2A, model ladder, JIT-generated QML tabs, comms-stream ingest, or a replacement file manager.
