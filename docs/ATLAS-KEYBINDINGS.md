# Atlas keybindings for Okbay on Omarchy

**Date:** 2026-09-13 (Europe/Zurich)  
**Status:** In-page set **implemented** (+ chrome parity 2026-09-13: ingest, workspace, edges, viewer, minimap, help).  
**Scope:** Match Omarchy’s binding + Super+K discovery pattern; Atlas chords that work under Chromium `--app=` kiosk.
**Hypr:** optional `contrib/hypr-bindings.lua` (`Super+Shift+K` → Atlas) — merge into `~/.config/hypr/bindings.lua` when ready.

---

## 1. Omarchy pattern summary

### 1.1 Super+K is a *viewer*, not a chord namespace

| Chord | What it runs | Role |
|-------|----------------|------|
| `Super + K` | `omarchy-menu-keybindings` | Interactive searchable list of **all** Hyprland binds (walker dmenu). Selecting a row re-dispatches that bind. |
| `Super + Alt + K` | `omarchy-menu-tmux-keybindings` | Tmux cheat sheet |
| `Super + Ctrl + K` | `omarchy-menu-herdr-keybindings` | Herdr cheat sheet |

**Cite:** `/usr/share/omarchy/default/hypr/bindings/utilities.lua` (`o.bind("SUPER + K", "Keybindings", "omarchy-menu-keybindings")`); manual <https://omarchy.org/manual/hotkeys/>; binary `/usr/bin/omarchy-menu-keybindings` (`--print` dumps the table).

So Atlas actions do **not** “nest under Super+K” as a prefix menu. The Omarchy pattern is:

1. Register real binds with **`o.bind(keys, description, dispatcher)`** so they appear in the Super+K list with a human description.
2. Put personal overrides in **`~/.config/hypr/bindings.lua`** (loaded after defaults; see comments there and `hyprland.lua`).
3. Optionally expose the same actions under **`Super + Space`** via menu JSONC extensions.

### 1.2 How apps / plugins register binds

- **Defaults:** `/usr/share/omarchy/default/hypr/bindings/{utilities,applications,tiling,clipboard,media,voxtype}.lua`
- **Helper:** `o.bind` in `/usr/share/omarchy/default/hypr/helpers.lua` — string → `hl.dsp.exec_cmd`, or tables `{ webapp=… }`, `{ omarchy=… }`, `{ tui=… }`, `{ launch=…, focus=… }`.
- **Web apps:** `omarchy-launch-webapp` / `omarchy-launch-or-focus-webapp` → Chromium `--app=<url>` (`/usr/share/omarchy/bin/omarchy-launch-webapp`).
- **User config:** `~/.config/hypr/bindings.lua` — add, or `hl.unbind` then rebind. Flags: `omarchy_default_bindings`, `omarchy_preinstalled_bindings` in `hyprland.lua`.
- **Inspect:** `omarchy-menu-keybindings --print` (or Super+K UI).

When replacing a bind, call `hl.unbind` for the chord before `o.bind`; otherwise Omarchy's original and the replacement can both fire. On Try Omarchy the Mac `⌘` key is Hyprland's `Super`: Okstratr's `Super+Shift+O` override must launch with `OMARCHY_PATH=/usr/share/omarchy`, while OKBay replaces `Super+Shift+K` with Atlas.

### 1.3 Okbay today (no Atlas key chords yet)

| Surface | Path | Key / discovery behaviour |
|---------|------|---------------------------|
| Menu extension | `~/.config/omarchy/extensions/okbay-menu.jsonc` (from `contrib/okbay-menu.jsonc`) | Super+Space → **Okbay** → Atlas / Reviews / desks |
| Bar widget | `BarWidget.qml` | Left click → Atlas; right click → Reviews panel |
| Panel toggle | Omarchy bar layout | **`Super + Ctrl + 1`** → toggle first right-bar panel (`benjsmith.okbay`) — see `utilities.lua` panel loop + `~/.config/omarchy/shell.json` |
| Atlas host | `Panel.qml` / `Overlay.qml` | Frameless `chromium --app=http://127.0.0.1:8766/atlas --start-fullscreen` (Qt WebEngine crash workaround) |
| In-page keys | `atlas-chrome.js` | Full set: `/` WASD arrows Ctrl/Alt+Arrow `l` `t` `e` `v` `i` `o` `m` `?` `=`/`[`/`]` `.` Enter `p` Esc. |
| Engine | Vendored `static/vendor/knowledge-atlas.js` (IIFE) | `hitTester.nearestInDirection` **present**; **no `keydown` listener** (keyboard lives only in React `KnowledgeAtlas.tsx`) |

Plugin manifest (`manifest.json`) has no keybind kind — Hyprland Lua / menu JSONC / in-page is the path.

---

## 2. Common Omarchy binds we might reuse or must avoid

### 2.1 Safe to reuse as *patterns* (not the same keys)

| Pattern | Omarchy example | Atlas takeaway |
|---------|-----------------|----------------|
| Descriptive `o.bind` so Super+K lists it | `SUPER + SHIFT + A` → “ChatGPT” webapp | Register “OKBay Atlas” open/focus the same way |
| Launch-or-focus webapp | `{ webapp = url, focus = true }` | Prefer focus existing Atlas window over spawning another |
| Bar panel by index | `SUPER + CTRL + 1..9` | Already toggles Okbay Reviews panel at index 1 on this guest |
| Universal clipboard into focused app | `SUPER + C/V/X` → `send_key_state` Ctrl chords | Proves Super chords never reach Chromium; WM injects instead |
| In-app Escape | Modal close in CE/Okbay | Keep Escape = dismiss modal / clear search |

### 2.2 Hard conflicts (do not steal)

From `/usr/share/omarchy/default/hypr/bindings/tiling.lua` + hotkeys manual:

| Chord | Default |
|-------|---------|
| **`Super + Arrow`** | Focus window in that direction |
| **`Super + Shift + Arrow`** | Swap window |
| **`Super + Alt + Arrow`** | Move window into group that direction |
| **`Super + Ctrl + Left/Right`** | Focus within tiling group |
| **`Super + K`** | Keybindings viewer |
| **`Super + F`** | Fullscreen |
| **`Super + /`** | Monitor scaling step |
| **`Super + Shift + O`** | Obsidian (preinstalled). **Okstratr may override this chord** — OKBay does not; Atlas stays on **Super+Shift+K**. |
| **`Super + C/V/X`** | Universal clipboard |

**Implication:** any Atlas action that the user phrased as `Super+Arrow` or `Super+Alt+Arrow` **cannot** be a global Hyprland bind without unbinding core tiling. Under Chromium `--app=`, **Super never reaches the page** anyway (Hyprland consumes it). In-atlas navigation must use **non-Super** chords (or a future Hyprland submap / pass-through while Atlas is focused).

### 2.3 Search focus candidates

| Chord | Status |
|-------|--------|
| `/` | Free at Hyprland level; classic “focus search”. **Best default** when focus is not already in an `<input>`. |
| `Ctrl + F` | Reaches Chromium; may open Chromium find-in-page unless we `preventDefault` on our handler. Prefer `/` first; optionally also Ctrl+F with preventDefault. |
| `Super + F` | **Taken** (fullscreen) — do not use. |

---

## 3. Proposed Atlas binding map

**Layer legend:**  
- **Page** = `keydown` in `atlas-chrome.js` / atlas host (works only while Atlas Chromium has seat focus).  
- **Hypr** = `o.bind` in user/plugin Hyprland Lua (shows in Super+K; works from anywhere).

| Action | Proposed chord | Layer | Notes |
|--------|----------------|-------|-------|
| Open / focus Atlas window | **`Super + Shift + K`** | Hypr | **`contrib/okbay-open-atlas.sh`** via `contrib/hypr-bindings.lua`. Exports `OMARCHY_PATH`, best-effort `omarchy-shell -q … summon` (never treats summon success as done), then **always** focus existing Chromium Atlas or launch `chromium --ozone-platform=wayland --app=http://127.0.0.1:8766/atlas` (uwsm-app when available). `setup.sh` installs the script + merges the bind. |
| Open Reviews panel | *(already)* **`Super + Ctrl + 1`** | Hypr | Keep; document. Optional alias in Okbay menu only. |
| **Focus search** | **`/`** (and optionally `Ctrl + F`) | Page | **Implemented.** Focus `#sidebar-search`, select-all if non-empty. Ignore when editable **except** Ctrl+F always (`preventDefault`). |
| **Label mode cycle** | **`l`** | Page | **Implemented.** Cycle `auto → on → off` (`Controls.cycleMode`). |
| **Types popup** | **`t`** | Page | **Implemented.** Toggle `#label-types-panel`. Esc closes. |
| **Expand/collapse sidebar groups** | **`=`** toggle-all; **`[`** / **`]`** collapse / expand all | Page | **Implemented** via `Sidebar.toggleAllGroups` / `collapseAllGroups` / `expandAllGroups`. |
| **Pan atlas view** | **`W A S D`** (repeat) | Page | **Implemented** via synthetic pointer drag on main canvas. Shift+WASD = larger step. Arrows reserved for node nav. |
| **Highlight / focus view-central (or current focus)** | **`.`** (period) | Page | **Implemented.** Re-focus `focusId` or nearest-to-centre node; toast via `toastFocus`. |
| **Arrows among neighbours (smooth)** | **`← ↑ → ↓`** | Page | **Implemented.** `hitTester.nearestInDirection` + soft highlight (`hover`/`select` + synthetic pointermove). Window keydown + canvas autofocus. |
| **Compass nearest** *(user: Super+arrows)* | **`Ctrl + Arrow`** | Page | **Implemented** (Ben confirmed). Stricter cone from viewport centre via `nearestInDirectionFromPoint`. Not Super (Hyprland). |
| **Walk anti-/clockwise around neighbours** *(user: Super+Alt+Left/Right)* | **`Alt + ←` / `Alt + →`** | Page | **Implemented** (Ben confirmed). Graph-neighbour angular ring; spatial nearby fallback. Helpers in `atlas-keys-helpers.js`. |
| **Edge mode cycle** | **`e`** | Page | **Implemented.** Cycle `auto → on → off` via `handle.setEdges` (vendor IIFE). |
| **Atlas ↔ Graph toggle** | **`v`** | Page | **Implemented.** Reload with `okbay.viewer` localStorage (classic D3 ↔ Atlas). |
| **Ingest (+)** | **`i`** | Page | **Implemented.** Prompt path → `POST /api/ingest` (confirm loop for privacy gate). |
| **Workspace switcher** | **`o`** | Page | **Implemented.** Panel: list / use / add / split via `/api/workspace/*`. |
| **Minimap toggle** | **`m`** | Page | **Implemented.** Toggle `canvas.atlas-minimap.hidden` (Atlas only). |
| **Help overlay** | **`?`** | Page | **Implemented.** In-chrome keybindings cheat sheet. |
| Enter / open | **`Enter`** / **`Shift + Enter`** | Page | **Implemented.** Enter = focus; Shift+Enter = openItem (modal). |
| Back | **`Backspace`** | Page | **Implemented.** `engine.back()` when not in search input. |
| Pin | **`p`** | Page | **Implemented.** `engine.pin` on nav/focus id. |
| Close modal / blur search | **`Escape`** | Page | **Implemented.** Modal → types panel → blur/clear search → blur editable. |

### 3.1 Why not literally Super+K nesting?

Registering Hypr binds with good `description` strings **is** how they “show under Super+K”. A nested Okbay submenu inside the keybindings viewer does not exist; use **Super+Space → Okbay** for hierarchical commands, and Super+K for flat discoverability of chords.

### 3.2 Optional Hypr-only companions (discoverable)

| Chord | Description | Command sketch |
|-------|-------------|----------------|
| `Super + Shift + K` | OKBay Atlas | launch-or-focus atlas URL |
| `Super + Shift + Alt + K` | OKBay Reviews | `omarchy-shell shell summon benjsmith.okbay '{"surface":"panel"}'` |

Keep the set small so Super+K stays scannable.

---

## 4. Implementation plan

### 4.1 Recommended split

| Concern | Where | Why |
|---------|-------|-----|
| Node nav, pan, search, labels, clockwise walk | **In-page `keydown`** (`atlas-chrome.js` + thin hooks on `handle.engine`) | Only place unmodified / Ctrl / Alt chords reach Chromium `--app=`. Matches CE PLAN keyboard semantics. |
| Open Atlas / Reviews from anywhere | **Hyprland `o.bind`** in `~/.config/hypr/bindings.lua` (later: ship a snippet under `contrib/hypr-bindings.lua`) | Shows in Super+K; matches webapp launch pattern. |
| Quickshell | **Do not** put Atlas nav in QML | Atlas is not a focused Quickshell surface today (toast overlay closes; panel is Reviews). `WlrKeyboardFocus.OnDemand` on panel is for Reviews only. |
| Engine IIFE gap | **Host chrome first**, optionally upstream IIFE later | Vendored IIFE has `nearestInDirection` + `tabIndex=0` but **zero keydown**. React `KnowledgeAtlas.tsx` ~553–618 is the reference implementation to port. |

### 4.2 Phased work

1. ~~**Page keymap module**~~ — `OkbayAtlasChrome.Keys` in `atlas-chrome.js` + `atlas-keys-helpers.js` (**done**).
2. ~~**Port arrow / Enter / Backspace / p**~~ (**done**, soft highlight via hover/select + pointermove).
3. ~~**Add** `/`, `l`, `t`, `=`/`[`/`]`, WASD, `.`, Ctrl+Arrow, Alt+Arrow~~ (**done**).
3b. ~~**Chrome parity** `e` edges, `v` viewer, `i` ingest, `o` workspace, `m` minimap, `?` help~~ (**done** 2026-09-13).
4. **Hypr snippet:** `contrib/hypr-bindings.lua` shipped; user merge still optional.
5. **Rebuild/vendor IIFE** only if we upstream keyboard into `packages/knowledge-atlas/src/iife.ts` (preferred long-term so CE wiki-view gets it too).
6. **E2E:** helper unit tests in `tests/test_atlas_key_helpers.mjs`; Playwright kiosk smoke still future.

### 4.3 Chromium `--app=` / kiosk focus issues

| Issue | Mitigation |
|-------|------------|
| Super chords never reach the page | Keep Atlas nav on Page layer; Hypr only for open/focus |
| Canvas needs focus for `keydown` | `tabIndex=0` already; call `canvas.focus()` after mount; also listen on `window` with target filters |
| Chromium Ctrl+F find bar | `preventDefault` on our Ctrl+F if we bind it |
| Fullscreen app steals or loses focus on open | After `execDetached`, optional `omarchy-launch-or-focus` pattern; click-to-focus still required once |
| Multiple Atlas windows | Always launch-or-focus; Overlay/Panel already `pkill -f 'chromium.*8766/atlas'` (harsh — prefer focus match later) |
| Hyprland tags Chromium as `chromium-based-browser` | Opacity/tile rules apply; no bind conflict by itself |
| GPU disabled in opener (`--disable-gpu`) | Unrelated to keys; keep in mind for key-repeat smoothness |

### 4.4 Angular neighbour walk (new)

No engine API yet. Sketch in chrome:

```text
neighbours = graph edges of anchor (fallback: nodes in hitTester radius)
sort by atan2(dy, dx) relative to anchor
index = current hover/focus in that ring
Alt+Right → neighbours[(index+1) % n]
Alt+Left  → neighbours[(index-1+n) % n]
then engine.hover / focus + light camera ease
```

---

## 5. Open questions for Ben

1. **Accept Ctrl/Alt instead of Super for in-Atlas compass / clockwise?**  
   **Confirmed by Ben (2026-09-11):** Ctrl+Arrow = compass; Alt+Arrow = anti-/clockwise walk. Do **not** use Super+Arrow (Hyprland).

2. **`Super + Shift + K` for open Atlas?**  
   **Shipped:** `contrib/okbay-open-atlas.sh` + `hypr-bindings.lua`; `setup.sh` merges into `~/.config/hypr/bindings.lua`. Root cause when it fails: missing `OMARCHY_PATH` for `omarchy-shell`.

3. **Arrows = spatial `nearestInDirection` (CE today) or true graph-neighbour BFS?**  
   React uses spatial. “Among neighbours” wording might mean edge-adjacent. Could do: arrows = spatial, Alt+arrows = ring of **graph** neighbours.

4. **Should we upstream keyboard into the IIFE** (shared with CE wiki-view) or keep Okbay-only chrome handlers until the next vendor bump?

5. **pkill vs launch-or-focus** for Atlas opener in QML — replace with sole-window focus before binding Super+Shift+K?

6. **Bar panel index** for `Super+Ctrl+1` is layout-dependent; if users reorder the right bar, the number moves. Document only, or add a dedicated `o.bind` that always summons Okbay?

---

## 6. Cite index (guest + host)

| What | Path |
|------|------|
| Super+K bind | VM: `/usr/share/omarchy/default/hypr/bindings/utilities.lua` |
| Arrow / tiling binds | VM: `/usr/share/omarchy/default/hypr/bindings/tiling.lua` |
| `o.bind` helper | VM: `/usr/share/omarchy/default/hypr/helpers.lua` |
| User override stub | VM: `~/.config/hypr/bindings.lua` |
| Keybindings menu | VM: `/usr/bin/omarchy-menu-keybindings` |
| Hotkeys manual | https://omarchy.org/manual/hotkeys/ |
| Okbay menu | VM: `~/.config/omarchy/extensions/okbay-menu.jsonc` |
| Shell / bar layout | VM: `~/.config/omarchy/shell.json` |
| Atlas opener | Host: `/workspace/okbay/Panel.qml`, `Overlay.qml` |
| Chrome / search | Host: `/workspace/okbay/src/okbay/static/atlas-chrome.js` |
| Vendored engine | Host: `/workspace/okbay/src/okbay/static/vendor/knowledge-atlas.js` |
| Keyboard reference | Host: `/workspace/curiosity-engine/packages/knowledge-atlas/src/react/KnowledgeAtlas.tsx` |
| `nearestInDirection` | Host: `…/src/core/hittest.ts` |
| PLAN keyboard list | Host: `…/PLAN.md` § Interaction |

---

## 7. Top recommendations (TL;DR)

1. **Treat Super+K as discovery** — register a couple of Hypr binds with clear descriptions; do not invent a Super+K prefix tree.  
2. **Put all Atlas navigation in-page** (`/`, arrows, WASD, `l`/`t`, Ctrl/Alt+Arrow). Super+Arrow is unavailable and conflicted.  
3. **Port React keyboard onto the IIFE host** (or upstream) — `nearestInDirection` is already vendored; keydown is the missing piece.  
4. **Add `Super + Shift + K`** → launch-or-focus Atlas; keep documenting **`Super + Ctrl + 1`** for Reviews.  
5. **Ben confirmed** Ctrl/Alt substitutions; arrows = spatial `nearestInDirection`, Alt+arrows = graph-neighbour angular ring (spatial fallback).


---

## 8. Chrome parity keybinds (2026-09-13)

| Chord | Control | API / surface |
|-------|---------|---------------|
| `i` / **+** button | Ingest path prompt | `POST /api/ingest` |
| `o` / workspace chip | List / use / add / split | `GET /api/workspace/list`, `POST /api/workspace/{use,add,split}` |
| `v` / **view:** button | Atlas ↔ classic Graph | localStorage `okbay.viewer` + reload |
| `e` / **edges:** button | Edge strokes auto/on/off | `KnowledgeAtlas` `setEdges` |
| `m` | Corner minimap show/hide | `canvas.atlas-minimap.hidden` |
| `?` / **?** button | Help overlay | `#atlas-help` |

Letters chosen to avoid `/` arrows WASD `l` `t` `p` `.` `=` `[` `]`.
