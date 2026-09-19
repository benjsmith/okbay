# Skill / shell inventory — okbay (Phase 5a)

Branch: `feat/skill-shell-rationalization`  
Charter: `/workspace/skill-shell-rationalization/docs/CHARTER.md` (locked 2026-09-18)  
Scope: this GitHub repo **is** the Omarchy plugin (`Panel.qml`, `BarWidget.qml`, …).

## Charter end-state (okbay row)

| Concern | End-state |
|--------|-----------|
| Install | okbay installs **CE + CM + okstratr** (plus itself) |
| Skins | **QML** panels / bar / overlay are the primary UI |
| Viewer mutex | **HTML off when QML on** (single viewer route) |
| Herdr | **On** via okbay/Omarchy only (not Mac Switchbay) |
| Settings | Shell settings **write okstratr harness+model registry** (SSOT) |
| Proxy | Same-origin reverse-proxy embeds for CE `:8766` / okstratr `:8767` under `/embed/…` (**no iframes**) |

> **Port note:** Today **okbay itself** listens on `:8766` (Python/Rust daemon + HTML Atlas). Charter end-state moves graph/atlas HTTP to **CE on `:8766`**; okbay becomes the Omarchy shell that proxies `/embed/ce/` + `/embed/okstratr/` and keeps QML chrome. Phase 5a mutex gates okbay's *current* HTML host so QML and HTML never both own the viewer.

## Current paths vs end-state

### A. Atlas / viewer surfaces

| Path | Role today | End-state | Gap |
|------|------------|-----------|-----|
| `Panel.qml` | Reviews + desks; Atlas click → Chromium `--app=http://127.0.0.1:8766/atlas` | QML panel owns Reviews; Atlas is QML skin **or** proxied CE embed — **not** a second HTML host when QML active | Mutex hooks added (Phase 5a); full QML Atlas skin still TODO |
| `Overlay.qml` | Overlay-only Atlas opener (Chromium) | Same mutex; prefer Panel kind | Guarded |
| `BarWidget.qml` | Left → Atlas Chromium; right → Reviews | Left → QML/atlas route; no HTML duplicate | Guarded |
| `src/okbay/static/atlas.html` + `/` `/atlas` | HTML Atlas host on `:8766` | Served only when `viewer_mode=html` | **Mutex implemented** (`viewer_mutex.py`) |
| `src/okbay/server.py` + `crates/okbayd` | Python + Rust daemons on `:8766` | Keep JSON API; HTML UI gated | Python gated; Rust parity TODO |
| `contrib/okbay-open-atlas.sh` | Super+Shift+K launch-or-focus Chromium | Honor `html_ui_enabled` / skip when QML | Follow-up |

### B. okstratr / observer HTML

| Path | Role today | End-state | Gap |
|------|------------|-----------|-----|
| okstratr `:8767` `/observer/` | HTML observer console | When `host=okbay`, okstratr HTML settings **disabled**; observer may be QML or proxied embed | Owned in okstratr repo; okbay must pass `host=okbay` |
| okbay desks → okstratr | Local desks router in `src/okbay/desks.py` | Desks/DAG/blackboard live in **okstratr**; okbay seats via registry | Migration later phases |
| Dynamic `/views/*` HTML decks | JIT decks from Herdr/okstratr | Allowed as sandboxed content **or** suppressed under QML mutex (treated as HTML UI) | Gated with `/` `/atlas` |

### C. Install CE + CM + okstratr

| Path | Role today | End-state | Gap |
|------|------------|-----------|-----|
| `contrib/setup.sh` | Builds okbayd, installs plugin QML, Hypr bind, systemd user unit | Also installs/links **curiosity-engine**, **curiosity-merge**, **okstratr** | **Not yet** — inventory only this phase |
| Skills under `skills/` | okbay-ask / curate / desk / views | Coexist with CE/CM/okstratr skills in Omarchy skill roots | Contract TBD Phase 6 |

### D. Herdr (okbay-only)

| Path | Role today | End-state | Gap |
|------|------------|-----------|-----|
| Omarchy + Herdr | Native agent multiplexer on Omarchy guests | **Herdr only via okbay/Omarchy**; Mac Switchbay uses direct/HTML harnesses | Documented here; seating goes through okstratr registry `backend=herdr` when host=okbay |
| `skills/okbay-views` | Mentions Herdr/okstratr decks | Keep; decks must not re-open HTML atlas when QML on | Mutex covers `/views/*` |

### E. Settings → okstratr registry

| Path | Role today | End-state | Gap |
|------|------------|-----------|-----|
| QML / future settings UI | None dedicated yet | Writes harness+model seats into **okstratr registry** (`okstratr harness …`) | Stub: document contract; no second allowlist in okbay |
| okstratr HTML settings | Exists on `:8767` | **Disabled** when hosted (`host=okbay\|switchbay`) | okstratr Phase 1 work |

## Mutex policy (implemented)

Module: `src/okbay/viewer_mutex.py`

| Mode | HTML `/` `/atlas` `/views/*` | JSON `/api/*` `/health` `/static/*` |
|------|------------------------------|--------------------------------------|
| `html` (default) | Served | Served |
| `qml` | **409** stub / JSON error | Served |

Resolution: `OKBAY_VIEWER_MODE` env → `~/.config/okbay/viewer.json` → default `html`.

CLI: `okbay viewer status|set html|qml`  
HTTP: `GET/POST /api/viewer`  
Status.json fields: `viewer_mode`, `html_ui_enabled`  
QML: `Panel.qml` / `Overlay.qml` / `BarWidget.qml` skip Chromium when `html_ui_enabled === false`.

## Herdr-only-on-okbay (contract)

1. **Host detection:** install / seat APIs treat Omarchy+okbay as `host=okbay`.
2. **Backend:** okstratr registry may enable `herdr` only for `host=okbay` (and Omarchy-native). Switchbay/Mac → `direct` (grok/claude/… CLIs).
3. **UI:** Herdr panes are Omarchy-native; okbay does not embed Herdr HTML. Observer chrome is QML or proxied okstratr routes — not a second HTML atlas.
4. **Finite jobs:** okstratr `herdr run-ready` remains the seat driver; okbay does not fork a parallel Herdr client.

## Settings → okstratr registry (contract)

1. okbay settings UIs (future QML) **only** mutate okstratr’s harness+model registry (same SSOT as Switchbay rail).
2. No okbay-local allowlist of models/harnesses.
3. When `host=okbay`, okstratr must refuse to serve its own HTML settings pages (hosted mode).
4. Read path: `okstratr harness list|detect`; write path: `okstratr harness enable|disable` (or HTTP equivalents under `/embed/okstratr/` once proxy lands).

## Session auto-start (C1)

Ben lock: **always** auto-start CE + okstratr with the okbay session (not opt-in).

| Module | Role |
|--------|------|
| `src/okbay/okstratr_supervisor.py` | Spawn/keep ``okstratr serve`` on `:8767` (`OKSTRATR_HOST=okbay`) |
| `src/okbay/ce_supervisor.py` | CE SSOT via okbay APIs on `:8766`; respect `viewer_mutex` (no HTML atlas when QML) |
| `src/okbay/core_skills.py` | Combined ensure + `/api/core-skills/status` shape |
| `okbay serve` | Calls `core_skills.ensure_started` on daemon start |

CLI: `okbay core-skills status|ensure` · HTTP: `GET /api/core-skills/status`

See also `docs/HERDR-AND-REGISTRY.md` §Session auto-start and umbrella `CONTRACT-AUTO-START-AND-NOTIFY.md`.

## Phase 5a deliverables checklist

- [x] This inventory
- [x] HTML↔QML mutex module + server gate + status fields
- [x] CLI + `/api/viewer`
- [x] QML Chromium suppress hooks
- [x] Tests for mutex policy
- [x] Herdr-only + registry contracts documented
- [x] Session auto-start CE + okstratr (C1) + `/api/core-skills/status`
- [ ] setup.sh installs CE+CM+okstratr (later slice)
- [ ] Rust okbayd HTML gate parity
- [ ] Same-origin `/embed/ce/` + `/embed/okstratr/` proxy
- [ ] Full QML Atlas skin (replace Chromium path)

## Related docs

- `docs/ATLAS-HOST.md` — current Chromium packaging
- `docs/ATLAS-KEYBINDINGS.md` — Super+Shift+K / in-page keys
- `docs/VIEWS.md` — views shell + dynamic decks
- Umbrella `CHARTER.md` / `DECISION-LOG.md`
