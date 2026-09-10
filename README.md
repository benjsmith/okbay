# Okbay

Compounding knowledge graph, Atlas overlay, and typed agent desks for [Omarchy](https://omarchy.org/).

Drop files. Do not organize them. Ask questions. The wiki gets stricter every time a proposed page survives review.

This is the v1 plugin designed after comparing [Switchbay](https://github.com/benjsmith/switchbay) with Omarchy. Switchbay is the existence proof. Okbay is the knowledge plane that rides Omarchy's existing agents, windows, skills, and plugin kinds — it does **not** wrap the Switchbay PWA.

Plugin id: `benjsmith.okbay`

## Name

`okbay` is not taken as a software product on PyPI, npm, or the Omarchy marketplace. Nearby names, not this project:

- PyPI [`okb`](https://pypi.org/project/okb/) — "Owned Knowledge Base", a different local search tool
- A few abandoned 0-star GitHub user pages named okbay / okBay
- Turkish given name Okbay; geneticist Aysu Okbay

## What v1 does

- Workspace at `~/Work/okbay/{vault,wiki}` (Omarchy agents already start in `~/Work`)
- Ingest copies sources into the vault and extracts a source-note wiki page with `extracted_from` provenance
- Agents **propose** wiki pages; you accept or reject in the Reviews panel. No blind writes.
- Atlas overlay searches nodes and can `okbay locate` the vault file / Hyprland window
- Standing desks `/curate` `/work` `/code` `/deck` are a tiny router + blackboard, not a bandit
- Skills land in the five roots Omarchy already maintains
- MCP server exposes the knowledge plane next to (not instead of) desktop MCP plugins
- HTTP on **127.0.0.1:8766** — never 8765

## Install on Omarchy

```sh
omarchy plugin add https://github.com/benjsmith/okbay.git --enable
# that only drops QML. Then run the visible installer:
git clone https://github.com/benjsmith/okbay
cd okbay
bash contrib/setup.sh
```

`omarchy plugin add` never executes install hooks. That is intentional.

## Use

```sh
okbay ingest ~/Downloads/lease.pdf
okbay ask "deposit rules"
okbay desk start curate
okbay reviews --json
okbay review accept 1
okbay locate deposit-rules
```

Bar widget: left click opens Atlas, right click opens Reviews. SETUP appears until `okbay setup` has run.

## Layout

```
manifest.json          Omarchy plugin contract
BarWidget.qml          bar pulse
Overlay.qml            Atlas chrome
Panel.qml              Reviews + desks
Service.qml            headless keep-alive
src/okbay/             CLI, wiki, graph, reviews, desks, HTTP
contrib/setup.sh       visible installer
contrib/okbayd.service systemd --user
contrib/mcp_server.py  stdio MCP
skills/                okbay-ask, okbay-curate, okbay-desk
```

## Compose, don't compete

| Neighbor | Plane |
|---|---|
| Omarchy default agent + Herdr | bodies |
| curiosity-engine / curiosity-merge | optional richer curator / split-merge |
| SIA (`khephri.sia`) | machine historian — different corpus |
| FileBlade / Nautilus | file tree; Atlas highlight target |
| omarchy-mcp-server | OS plane MCP |

## v1 is not

Power/Zen PWA, AG-UI, A2A, model ladder, JIT-generated QML tabs, comms-stream ingest, or a replacement file manager.
