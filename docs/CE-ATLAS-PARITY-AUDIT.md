# CE Atlas → Okbay parity audit

**Date:** 2026-09-11  
**Scope:** Audit only — no port implementation.  
**Goal:** Actionable inventory for the next **okbayd data-bridge** step and Biocure (~40k nodes / ~180k edges) canvas parity via option 3 (frameless Chromium kiosk).  
**Related:** `docs/TESTING-FEEDBACK-TODO.md` (Atlas surface / option 3 locked).

---

## 1. Architecture map

Three layers. Okbay should treat **knowledge-atlas** as the canvas engine and **wiki-view chrome** as optional host UI; the **data adapter** is the seam that must be rebuilt against okbayd.

```
┌─────────────────────────────────────────────────────────────────┐
│ Host chrome (CE: wiki-view)                                     │
│  index.html · sidebar.js · modal.js · subgraph.js · theme.js    │
│  atlas.js (glue) · main.js (orchestrator) · fuse.min.js         │
│  Owns: Fuse search, type-grouped wiki list, doc modal,          │
│        #page= hash, classic/atlas chooser, label/physics UI     │
└────────────────────────────┬────────────────────────────────────┘
                             │ KnowledgeAtlas.mount(container, {data})
                             │ onOpenItem → #page=<id>
┌────────────────────────────▼────────────────────────────────────┐
│ @curiosity/knowledge-atlas (packages/knowledge-atlas)            │
│  IIFE: static/vendor/knowledge-atlas.js (~96 KB)                │
│  window.KnowledgeAtlas.mount → CuriosityDataSource(CEData)      │
│  → AtlasEngine → hybrid layout + CanvasRenderer + AtlasMinimap  │
└────────────────────────────┬────────────────────────────────────┘
                             │ AtlasDataSource / CEData
┌────────────────────────────▼────────────────────────────────────┐
│ Data                            CE today          Okbay today   │
│ Payload                         data.json         GET /graph    │
│ Adapter                         curiosity.ts      (none)        │
│ Theme palette                   data.palette      GET /api/theme│
└─────────────────────────────────────────────────────────────────┘
```

### 1.1 knowledge-atlas core (engine)

| Area | Path | Key symbols |
|------|------|-------------|
| Public types / budgets | `packages/knowledge-atlas/src/core/types.ts` | `KnowledgeItem`, `SceneBudget`, `DEFAULT_BUDGET`, `AtlasDataSource`, `AtlasConfig`, `AtlasController`, `AtlasEvent` |
| Engine | `…/core/engine.ts` | `AtlasEngine`, `effectiveBudget()`, `setViewScale`, `setPhysics` |
| Graph index | `…/core/graphindex.ts` | `GraphIndex` |
| Scene pipeline | `…/core/scene/builder.ts`, `ranking.ts`, `discovery.ts`, `aggregate.ts`, `landmarks.ts` | `buildScene`, MMR selection, six discovery classes |
| Log-space shells | `…/core/scene/shells.ts` | `DEFAULT_CORE_CAPACITY` (360), `MAX_CORE_CAPACITY` (10k), `shellOfRank`, `shellCount`, `buildShells`, `viewScaleToFit`, `TARGET_PX_PER_NODE` (2850) |
| Layouts | `…/core/layout/{hybrid,force,focus,hyperbolic,adaptive,adaptiveHybrid}.ts` | `hybridLayout`, `isFullGraphScene`, `coreRadius` |
| Geometry | `…/core/geometry.ts` | squircle / core area |
| Hit testing / trails / zoom | `…/core/hittest.ts`, `trails.ts`, `zoom.ts` | |
| Canvas renderer | `…/renderer/canvas.ts`, `theme.ts`, `minimap.ts` | `CanvasRenderer`, `AtlasMinimap`, `resolveTheme` |
| Interaction | `…/interaction/{camera,hover,tooltip,lens,traversal}.ts` | pan/zoom, boundary hover dwell, `LensTraversal` |
| CE adapter | `…/datasources/curiosity.ts` | `CEData`, `CuriosityDataSource`, `indexFromCEData`, `normalizeId`, `canonicalType`, `ceItem` |
| Local / remote / scaled | `…/datasources/{local,remote,scaled}.ts` | `LocalSceneSource`, `RemoteDataSource` |
| Package entry | `…/src/index.ts` | re-exports core + datasources + renderer |
| IIFE mount | `…/src/iife.ts` | `mount()`, `MountOptions`, `MountHandle` |
| React host example | `…/examples/switchbay/AtlasTab.tsx` | `CuriosityDataSource` + `<KnowledgeAtlas>` |
| Design / perf | `…/docs/atlas-engine-design.md`, `performance.md`, `extension-points.md`, `PLAN.md` | |

**Invariant (chrome-free):** engine emits `AtlasEvent` / accepts `AtlasController`; it does **not** own search, wiki modal, or sidebar (`README.md`, `extension-points.md` §6).

### 1.2 wiki-view chrome (CE host)

| File | Role |
|------|------|
| `skills/curiosity-engine/template/wiki-view/index.html` | Layout: `#sidebar`, `#graph-pane`/`#graph`, modal, controls, script includes |
| `static/main.js` | Fetch `data.json`, init modules, `#page=` routing, atlas vs classic |
| `static/atlas.js` | Size gate (>360), `KnowledgeAtlas.mount`, Graph-compatible facade |
| `static/sidebar.js` | Type-grouped wiki browser + **Fuse.js** search |
| `static/modal.js` | Wiki page browser (`body_html`, properties, wikilinks) |
| `static/subgraph.js` | 1-hop neighbour pane inside modal |
| `static/graph.js` | Classic D3 force viewer (visibility/highlight model) |
| `static/theme.js` | Light/dark `data-theme` |
| `static/edit.js` | In-viewer edit (CE-only; skip for Okbay minimum) |
| `static/vendor/knowledge-atlas.js` | Vendored IIFE (~95 618 B) |
| `static/vendor/fuse.min.js` | Fuse (~23 850 B) |
| `static/vendor/d3.min.js` | Classic viewer only |

### 1.3 Okbay today (gap)

| Piece | Path | Notes |
|-------|------|-------|
| Atlas host | `src/okbay/static/atlas.html` + `atlas-chrome.js` + vendor JS | **Slice 2:** KnowledgeAtlas.mount + Fuse sidebar + slim wiki modal + focus |
| Graph API | `src/okbay/graph.py`, `crates/okbayd/src/graph.rs` | `{nodes, edges, pages}` — **not** `CEData` |
| Theme API | `src/okbay/theme.py` → `GET /api/theme` | Switchbay CE type palette already present |
| Search | Fuse in `atlas-chrome.js` (+ `GET /atlas/search` server) | Client Fuse over `/api/atlas/data` nodes |
| Locate | `src/okbay/locate.py`, `GET /api/locate` + `/locate` | Prefer Omarchy Nautilus (`--select` / `--new-window`, optional `uwsm-app`); fall back to `xdg-open`; accepts `stem=` or `q=` |
| Daemon | `server.py` / rust `okbayd` on `127.0.0.1:8766` | Serves `/` `/atlas` HTML |

---

## 2. CE UX surface inventory

Minimum Okbay target (from product lock): **log-space shells/border, fast Fuse search, wiki + source browsers, file highlighting**, plus CE canvas performance feel.

### 2.1 Log-space shells / border

| Behaviour | Where |
|-----------|--------|
| Cosmological shells (log₁₀ rank bands 1k / 10k / 100k) | `shells.ts` — `shellOfRank`, `buildShells` |
| Hybrid layout: force core + compressed rim / wall | `hybrid.ts`, IIFE `config.layout: 'hybrid'` |
| Squircle boundary + `boundaryShape` | `geometry.ts`, `AtlasConfig.boundaryShape` |
| First paint fits whole corpus (not type-cluster bubbles) | `atlas.js` sets `corpusSize`, `coreCapacity`, `maxVisibleNodes` to page count; `viewScaleToFit` |
| Shell quotas (granular near → smeared far) | `SHELL_NODE_QUOTA` / `SHELL_AGG_QUOTA` in `shells.ts` |

**CE wiki-view mount policy** (`atlas.js` ~205–224): for Atlas mode it **pins full-graph capacity** to corpus size and sets `maxAggregates: 0`, `maxEdges: max(900, edges.length)` — i.e. Biocure-scale CE opens as an individual-node log-boundary scene, not the default 460-node bounded scene. **Okbay product decision:** same hard policy — aggregates (type-bubble shells) unsupported / not offered; `maxAggregates: 0` only (see §4 / §7 / §8).

### 2.2 Search (Fuse)

| Behaviour | Where |
|-----------|--------|
| Client Fuse over title / type / props | `sidebar.js` — `new Fuse(allRecords, { keys: title 0.7, type 0.1, props 0.2, threshold: 0.35, ignoreLocation: true })`, `limit: 200` |
| Idle: type-grouped list; query: flat ranked | `renderGrouped` / `renderFlat` |
| Row click → `#page=<id>` | hash contract |

**Okbay (Slice 2):** client Fuse in `atlas-chrome.js` over bridge nodes (same weights as CE).

### 2.3 Wiki browser

| Behaviour | Where |
|-----------|--------|
| Sidebar type groups (Projects…Sources…) | `sidebar.js` `TYPE_ORDER` / `TYPE_LABEL` |
| Modal: title, properties, `body_html`, ESC/backdrop | `modal.js` |
| Wikilink navigation in body | `a.wikilink[data-page]` |
| 1-hop subgraph in modal | `subgraph.js` |
| Open from atlas double-click / `item-open-requested` | `iife.ts` → `onOpenItem` → `#page=` |

**Okbay (Slice 2):** lazy `GET /api/atlas/page?stem=` (+ `/api/wiki/<stem>`); bridge still stubs `body_html: ""`.

### 2.4 Source browser

In CE, “sources” are first-class **page types** (`type: source`) in the same sidebar/modal, plus frontmatter `properties.sources` (vault provenance). Classic graph **hides** source-type nodes unless focused (`graph.js` visibility model: `data-vis="hidden"` for sources).

| Behaviour | Where |
|-----------|--------|
| Sources group in sidebar | `TYPE_ORDER` includes `source` |
| Modal properties order includes `sources` | `modal.js` `order = ['created','updated','sources']` |
| Adapter extracts `meta.sources` from props | `curiosity.ts` `ceItem` |
| Classic hide-sources-until-focus | `graph.js` (Atlas canvas uses type colour; sources remain in index) |

**Okbay:** nodes carry `sources: string[]` and `files: string[]` (resolved vault paths) already — good for a source/file browser without inventing CE page types, but type/kind fidelity is still weak (many pages `kind: note`).

### 2.5 File highlighting / locate

| CE | Okbay |
|----|-------|
| Provenance via `properties.sources`; no separate “reveal in file manager” in wiki-view | `locate.locate(stem)` resolves wiki path + source files; optionally `xdg-open` parent; Hypr hint |
| Focus neighbourhood highlight in classic (`focus`/`neighbour`/`dim`) | Naive atlas toggles `.focus` on SVG node/edges; broken `/locate?q=` vs API `stem`/`q` |

**Parity ask:** selecting a node highlights it in-atlas **and** can call `okbay locate` / `/api/locate?stem=` to reveal vault files (stretch ties to Omarchy file browser).

### 2.6 Minimap / controls / view modes

| Surface | Where |
|---------|--------|
| Corner minimap (whole-graph field + viewport box) | `renderer/minimap.ts`, mounted in `iife.ts` |
| Labels: auto/on/off + per-type filter | `index.html` controls + `atlas.js` `initAtlasControls` → `handle.setLabels` |
| Physics sliders (charge/link/collide) | settings panel → `handle.setPhysics` |
| Classic ↔ Atlas chooser | `viewer-mode` button; `MIN_ATLAS_PAGES = 360`; `?viewer=atlas` |
| Theme light/dark | `theme.js` + `data-theme`; IIFE MutationObserver re-resolves palette |
| Pan (reversible camera), wheel/pinch zoom | `iife.ts` camera + `setViewScale` |
| Aggregate tooltip / long-press | `interaction/tooltip.ts` |
| Experimental lens traversal | `LensTraversal` — remote/cloud primitive; not required for Biocure local |

### 2.7 What Okbay naive atlas already has (keep / replace)

- Header search + left hit list — **replace** with Fuse + type groups.
- Theme poll `/api/theme` — **keep**; feed into CE `palette` / CSS vars.
- `/locate` on select — **keep** (fix query param); map to highlight + reveal.
- SVG circle — **replace** with `KnowledgeAtlas.mount`.

---

## 3. Data contract

### 3.1 What `CuriosityDataSource` / `CEData` needs

From `datasources/curiosity.ts` and `PLAN.md` §2.1:

```ts
type CEData = {
  workspace: string;
  generated_at: string;                 // ISO8601
  palette: Record<string, string>;      // type → hex (singular+plural aliases OK)
  nodes: Array<{
    id: string;                         // suffix-less; path may keep .md
    path: string;
    type: string;                       // opaque; canonicalised by adapter
    title: string;
    degree: number;
  }>;
  edges: Array<{
    source: string | { id: string };    // D3 mutation tolerant
    target: string | { id: string };
    type: string;                       // wikilink | depicts | …
    confidence?: number;
    origin?: string;
  }>;
  pages: Record<string, {
    id: string;
    title: string;
    type: string;
    path: string;
    properties: Record<string, unknown>; // sources[], created, updated, …
    body_html: string;                   // required for wiki modal
  }>;
  scan_staleness?: unknown;              // optional CE banner
};
```

**Adapter behaviours Okbay bridge must preserve or reimplement:**

| Rule | Symbol |
|------|--------|
| Strip `.md` from ids | `normalizeId` |
| Plural/table/prefix type canonicalisation | `canonicalType`, `TYPE_CANONICAL`, `PREFIX_TO_TYPE` |
| Split `[con]` title prefixes into `meta.titlePrefix` | `ceItem` / `TITLE_PREFIX_RE` |
| `nodes` order drives layout seed stability; page-only entries appended | `indexFromCEData` |
| `palette` exposed on datasource | `CuriosityDataSource.palette` |
| Overview for minimap; edges omitted if `graph.size >= 5000` | `getOverviewScene` |

**Engine item shape after adapt:** `KnowledgeItem { id, type, title, meta: { titlePrefix?, path?, sources?, degree?, properties? } }`.

**`AtlasDataSource` methods:** `getScene(request)`, `getItem(id)`, `getExplanation(request)`, optional `getOverviewScene`, optional `palette`.

### 3.2 How okbay `/graph` differs

Python (`graph.py`) / Rust (`graph.rs`) emit approximately:

```json
{
  "nodes": [
    {
      "id": "<stem>",
      "title": "...",
      "kind": "note|hub|missing|…",
      "path": "...",
      "sources": ["relative-or-name"],
      "files": ["/abs/resolved/vault/..."]
    }
  ],
  "edges": [
    { "source": "...", "target": "...", "type": "wikilink" },
    { "source": "...", "target": "file:…", "type": "extracted_from" }
  ],
  "pages": 39122
}
```

| Field | CE `data.json` | Okbay `/graph` | Bridge action |
|-------|----------------|----------------|---------------|
| Type key | `type` | `kind` | Map `kind` → `type`; run through `canonicalType` |
| Degree | `nodes[].degree` | absent | Compute from adjacency |
| `pages` | Record of page docs + `body_html` | **integer count** | Rename count; add real `pages` map or separate page API |
| `palette` | in payload | via `/api/theme`.kinds | Inject theme.types into `CEData.palette` |
| `workspace` / `generated_at` | present | absent | Fill from okbay paths / mtime |
| Missing stubs | via kuzu drift | `kind: missing` | Keep as unclassified/missing |
| File edges | Cites not in viewer export | `extracted_from` + `file:` targets | Either materialise source nodes or keep as meta-only (prefer meta + locate) |
| Edge endpoint objects | possible | always strings | OK |
| Body HTML | pre-rendered | raw markdown on disk | Render on bridge or lazy endpoint |

**Biocure fidelity issues (already tracked):** CE frontmatter `type:` often lands as okbay `kind: note`; edge set is wikilink-only vs CE Kuzu extras — colors and density will diverge until kind mapping + optional edge enrichment land.

### 3.3 Suggested bridge output

Preferred for first slice: **okbayd endpoint that returns CE-compatible JSON**, e.g. `GET /api/atlas/data` or enrich `/graph?format=ce`, so the stock IIFE + `CuriosityDataSource` work unchanged:

1. Map each node → `{ id, path, type: kind, title, degree }`.
2. Build `pages[id]` with at least `{ id, title, type, path, properties: { sources }, body_html }` (body can be stub `""` for canvas-only slice).
3. Attach `palette` from `theme.type_palette()`.
4. Filter or rewrite `extracted_from` / `file:` edges so `GraphIndex` does not create thousands of non-page litter nodes (or add proper `source`-type nodes).
5. Keep serving raw `/graph` for status/CLI.

---

## 4. Performance model

Sources: `docs/performance.md`, `shells.ts`, `engine.ts` `effectiveBudget`, `curiosity.ts` overview, wiki-view `atlas.js` mount config.

### 4.1 Default scene budgets (`DEFAULT_BUDGET`)

| Budget | Default |
|--------|---------|
| `maxNodes` | 460 |
| `maxAggregates` | 40 |
| `maxEdges` | 900 |
| `maxBundles` | 24 |
| `maxLabels` | 60 |

Viewport scales budgets by √(area / 1200×800), clamp ×[0.5, 2].

### 4.2 Capacity / shells

| Constant | Value |
|----------|-------|
| Classic core capacity | 360 (`DEFAULT_CORE_CAPACITY`) |
| Density | ~2850 px² / node |
| Production max visible | 10 000 (`MAX_CORE_CAPACITY`) |
| Experimental max | 100 000 |
| Shell milestones | ranks 1k → 10k → 100k → ∞ |

**Edge suppression:** if not full-graph-resident and `capacity >= 5000` → `maxEdges = 0`; at `>= 2000` edges capped to ~0.35× capacity. Overview scene also sets `maxEdges = 0` when `graph.size >= 5000`.

### 4.3 Cost notes (harness, pessimistic container)

| Stage | Typical |
|-------|---------|
| BFS harvest | &lt; 5 ms, visit-capped `40 × maxNodes` |
| Ranking / MMR | dominant on dense graphs; O(harvest × maxNodes) |
| Force pre-warm | ~70 ms (350 ticks) — hybrid core |
| Canvas draw | 1–3 ms/frame, ≤ ~10³ primitives in bounded mode |
| Warm scene build | ~22 ms (400-node); bounded even for 1M procedural |

**Idle:** no rAF when static. Transitions ~300 ms.

### 4.4 Biocure (~40k / ~180k) implications

| Approach | Implication |
|----------|-------------|
| **A. CE wiki-view policy** (pin `coreCapacity = corpusSize`, all edges, `maxAggregates: 0`) | **Okbay shipped policy.** Full 40k-node force field + ~180k edges in memory. Proven in CE around 28–38k pages, but cold start / layout cost is large; overview edge omit at ≥5k helps minimap only. Risk: multi-second first layout, high RAM. Aggregates dropped by product decision — not an optional toggle. |
| **B. Engine default budgets** (460/900 + shells) | *(Historical / CE engine default — not offered in Okbay.)* Fast first paint; log shells carry the rest; zoom raises capacity toward 10k. |
| **C. Hybrid compromise** | *(Historical mis-mount — caused type-bubble aggregates; not a live Okbay option.)* First paint: viewScale-to-fit with `maxVisibleNodes: 10000`, shells beyond; defer full edge set; promote edges when zoomed. |

**Payload size:** full `/graph` JSON for Biocure is already called out as heavy (`TESTING-FEEDBACK-TODO`). Bridge should avoid shipping `body_html` for all 39k pages in the first canvas slice (lazy page fetch).

**Memory:** local `GraphIndex` holds all items + adjacency; client RAM scales with corpus for local adapter (unlike remote `ScaledDataSource`). 40k is inside the “≤ ~10⁵ in-page” design band (`atlas-engine-design.md` §4).

---

## 5. Port strategy options (ranked)

### Rank 1 — **Vendor IIFE + slim Okbay chrome** (recommended)

- Copy `knowledge-atlas.js` (+ optionally `fuse.min.js`) into `okbay/static/vendor/`.
- Replace `atlas.html` with a slim host: mount canvas, Fuse sidebar, thin modal, theme from `/api/theme`.
- Serve **CE-shaped** JSON from okbayd (`/api/atlas/data`).
- Open via existing option-3 Chromium `--app=http://127.0.0.1:8766/atlas`.

**Pros:** Matches CE production embedding path (`examples/curiosity-engine/README.md`); ~96 KB engine; no React; chrome-free events for locate/bar later.  
**Cons:** Must maintain vendor ritual after engine upgrades; need data bridge.

### Rank 2 — **Full wiki-view template fork**

- Vendor entire `template/wiki-view/` and point `main.js` at okbayd CE payload.

**Pros:** Maximum chrome parity (subgraph, label panels, physics, edit hooks).  
**Cons:** CE edit/upload/scan-staleness baggage; heavier HTML; still needs identical data bridge; Omarchy theming fight.

### Rank 3 — **React `AtlasTab` pattern**

- Use `@curiosity/knowledge-atlas/react` as in `examples/switchbay/AtlasTab.tsx`.

**Pros:** Clean if Okbay gains a React shell.  
**Cons:** Okbayd is static HTML today; adds toolchain without product need.

### Rank 4 — **iframe CE viewer**

- Run CE viewer.sh against a mirrored wiki and iframe it.

**Pros:** Zero engine port.  
**Cons:** Dual daemons, path/theme/locate disconnect, poor Omarchy kiosk story — reject for parity track.

### Rank 5 — **Native QML Scene Graph** (explicitly later)

- Only after CE parity on Chromium kiosk (`TESTING-FEEDBACK-TODO`).

---

## 6. Biocure parity checklist

### Must-have (minimum CE look/feel/performance)

- [x] **Data bridge:** okbayd emits CE-compatible payload via `GET /api/atlas/data` (`type`←`kind`/`type:`, `degree`, `pages` map stubs, `palette` from theme) — Slice 0
- [ ] **Vendor engine:** ship `knowledge-atlas.js`; `KnowledgeAtlas.mount` into `#graph`
- [x] **Hybrid canvas:** `layout: 'hybrid'`, pan/zoom/focus (Policy A = full-graph force; no aggregate rim)
- [x] **Individual-node policy:** Policy A — `maxAggregates: 0`, `coreCapacity = corpusSize` (no type-group bubbles)
- [ ] **Type colors:** Switchbay/Omarchy palette via `palette` / `resolveTheme`
- [ ] **Fuse search:** client Fuse (≥ title+kind+sources), ≤200 hits, focus-on-select
- [ ] **Wiki browser:** type-grouped list + page open (modal or pane); hash or equivalent routing
- [ ] **Source browser:** list/filter `kind/type=source` **or** provenance `sources`/`files` per node
- [ ] **In-atlas highlight:** focus node + neighbour emphasis (engine selection/focus or host overlay)
- [x] **Minimap:** present when full-graph scene (Policy A) or after overview solve
- [ ] **Biocure smoke:** open full ~40k graph via okbayd without UI freeze &gt; few seconds; interact 60fps after settle
- [ ] **Option 3 host:** frameless Chromium kiosk loads new atlas (not SVG circle)

### Stretch (Omarchy / Okbay uplifts)

- [ ] Live Omarchy theme hot-reload (keep `/api/theme` poll or file watch)
- [ ] Bar summon → Atlas workspace (left-click chip)
- [ ] Wire select → `GET /api/locate?stem=` (fix query bug); optional suppress auto-`xdg-open`
- [x] Native file browser / Hypr reveal polish (Nautilus `--select` + `uwsm-app`; xdg-open fallback)
- [ ] Label type picker + physics sliders (CE chrome parity)
- [ ] 1-hop subgraph pane (`subgraph.js`)
- [ ] CE kind fidelity: ingest `type:` frontmatter → `kind`
- [ ] Richer edges (depicts / cites) if available
- [ ] Discovery horizon chrome (engine already computes; host UI optional)
- [ ] Remote/bounded scenes if RAM hurts (`RemoteDataSource` / server harvest)

### Explicit non-goals for first port

- [ ] CE in-modal editing (`edit.js`)
- [ ] Vault upload from sidebar
- [ ] Scan-staleness banner
- [ ] Classic D3 viewer chooser (Atlas-only is fine for Okbay)
- [ ] Quickshell WebEngine (frozen)
- [ ] QML native atlas

---

## 7. Recommended first implementation slice

**Smallest vertical slice that proves canvas parity on Biocure through okbayd:**

### Slice 0 — Data bridge ✅ landed (2026-09-11)

1. **`okbay.atlas_ce`** (Python) + **`crates/okbayd/src/atlas_ce.rs`** (Rust):
   - Input: `graph.load()` + `theme.type_palette()` / `theme::atlas_theme()`.
   - Output: minimal `CEData` with stub `body_html: ""`.
   - Computes `degree` (non-`file:` edges); maps `kind`→`type` with CE-style plural/canonicalisation; prefers wiki frontmatter `type:` when present.
   - Drops `file:` / `extracted_from` edges from the atlas index; keeps `properties.sources`.
   - Sets `workspace`, `generated_at`, `palette`, `page_count` (integer; separate from `pages` object).
2. **`GET /api/atlas/data`** (alias `/atlas/data`). `/graph` unchanged.
3. Tests: `tests/test_atlas_ce.py`. Curl example:
   ```bash
   curl -s http://127.0.0.1:8766/api/atlas/data \
     | jq '{workspace, page_count, nodes:(.nodes|length), sample:(.nodes[:2]), palette:(.palette|keys[:6])}'
   ```
4. Locate query fix: `/api/locate` and `/locate` accept `stem=` or `q=`; atlas.html uses `stem=`.

**Caveat:** Biocure pages historically stored as `kind: note` in graph.json; colors improve after wiki `type:`→kind parse (now in `wiki.parse_page`) + **graph rebuild**. Optional `enrich_wiki_types=True` can re-scan frontmatter but is expensive at Biocure scale — not used on the hot `/api/atlas/data` path.

### Slice 1 — Canvas mount ✅ landed (2026-09-11)

1. Vendored `knowledge-atlas.js` (+ `fuse.min.js` for Slice 2) → `src/okbay/static/vendor/`.
2. Rewrote `atlas.html`: full-viewport `#graph`, loads `/static/vendor/knowledge-atlas.js`, fetches `/api/atlas/data` + `/api/theme`, mounts:

```js
// Hard maxAggregates:0 (aggregates unsupported) — landed 2026-09-11; aggs status stripped later
KnowledgeAtlas.mount(graphEl, {
  data: ceData,
  config: {
    layout: 'hybrid',
    corpusSize: corpusSize,
    coreCapacity: Math.max(1, corpusSize),
    maxVisibleNodes: Math.max(1, corpusSize),
    budget: {
      maxNodes: Math.max(1, corpusSize),
      maxAggregates: 0,
      maxEdges: Math.max(900, edges.length),
    },
  },
  onOpenItem: (id) => { /* hash → modal + locate */ },
});
```

3. Static routes: Python `GET /static/...` from package `static/`; Rust embeds vendor JS via `include_bytes!` for `/static/vendor/knowledge-atlas.js` (+ fuse).
4. Naive SVG circle layout removed as primary viewer. Fuse sidebar / wiki modal deferred to Slice 2.
5. Option-3 kiosk still points at `/atlas` — confirm shells/border, pan/zoom, type colours on Biocure next.

### Slice 2 — Chrome minimum ✅ landed (2026-09-11)

1. Vendored Fuse loaded from `/static/vendor/fuse.min.js`; slim sidebar in `atlas-chrome.js` + `atlas.html` (type-grouped idle / flat Fuse hits; weights title 0.7 / type 0.1 / props 0.2, threshold 0.35, limit 200).
2. Slim modal: lazy `GET /api/atlas/page?stem=` (aliases `/atlas/page`, `/api/wiki/<stem>`) returns markdown + minimal `body_html` — **not** embedded in `/api/atlas/data`. ESC / backdrop close; sources from `properties.sources`.
3. On search select / open / `#page=<id>`: `handle.engine.focus(id, 'user')` + locate `/api/locate?stem=` + modal. Neighbour emphasis via engine roles when scene rebuilds (no engine fork).
4. Python (`server.py` + `wiki.page_payload`) and Rust (`wiki::page_payload` + `http.rs`) both serve the page endpoint; Rust also embeds `/static/atlas-chrome.js`.

### Acceptance for “canvas parity proven”

- Biocure loads via okbayd; hybrid atlas visible (not SVG ring).
- Log-compressed rim/shells or full individual-node field per chosen policy.
- Focus + zoom remain interactive after first layout.
- At least one type colour matches Switchbay palette (e.g. concept/entity once kinds exist).

---

## Appendix A — Key file index (absolute)

```
/workspace/curiosity-engine/packages/knowledge-atlas/
  src/core/types.ts
  src/core/engine.ts
  src/core/scene/shells.ts
  src/datasources/curiosity.ts
  src/iife.ts
  docs/atlas-engine-design.md
  docs/performance.md
  examples/switchbay/AtlasTab.tsx

/workspace/curiosity-engine/skills/curiosity-engine/template/wiki-view/
  index.html
  static/{atlas,main,sidebar,modal,graph,subgraph,theme}.js
  static/vendor/{knowledge-atlas.js,fuse.min.js,d3.min.js}

/workspace/okbay/
  src/okbay/static/atlas.html
  src/okbay/static/atlas-chrome.js
  src/okbay/static/vendor/{knowledge-atlas.js,fuse.min.js}
  src/okbay/{server,graph,theme,locate,search,atlas_ce}.py
  crates/okbayd/src/{http,graph,locate,theme,atlas_ce}.rs
  docs/TESTING-FEEDBACK-TODO.md
  docs/CE-ATLAS-PARITY-AUDIT.md   ← this file
```

## Appendix B — Symbol cheat sheet

| Need | Call |
|------|------|
| Mount | `window.KnowledgeAtlas.mount(container, MountOptions)` |
| Focus | `handle.engine.focus(id, 'user'\|'system')` |
| Labels | `handle.setLabels(mode, types?)` |
| Physics | `handle.setPhysics({ charge, link, collide })` |
| Events | `handle.engine.on(cb)` / `AtlasEvent` |
| Adapt CE JSON | `new CuriosityDataSource(data)` or mount’s built-in path |
| Normalize | `normalizeId`, `canonicalType`, `indexFromCEData` |

---

*Slice 0–2 landed. 2026-09-11: Policy A mount (no aggregates) + minimap path fixed via full-graph capacity — see §8. Aggregates dropped by product decision; host UI no longer reports `aggs=`.*

---

## 8. Aggregate / minimap / rectangular-core diagnosis (2026-09-11)

**Product decision (follow-up):** Okbay does **not** offer aggregates. Policy A / `maxAggregates: 0` is hard — not an optional budget. Host UI no longer surfaces `aggs=` / `aggregateCount` in the status bar, `document.title`, or `dataset.atlasAggs`. Policy C remains documented only as the historical mis-mount that produced type-bubble shells.

### Root causes

| Symptom | Cause |
|---------|--------|
| Numbered type bubbles (1324, 496, …) in cosmological shells | Okbay mounted **Policy C** (`maxVisibleNodes: 10000` only). Engine `DEFAULT_BUDGET.maxAggregates = 40` still applied → `shells.ts` / `aggregate.ts` emit type-grouped aggregates on the rim. |
| Rectangular / squircle central cluster (not network) | Bounded hybrid scene (`!isFullGraphScene`) force-lays out only the core slot inside a squircle wall; rim is shells/aggs. Full-graph-resident (`aggregates=[], no shell nodes`) uses unconstrained force = network structure. |
| Missing minimap | `AtlasMinimap` always mounts but stays `hidden` until `overviewLayout`/`overviewScene` exist. Primary scene only fills overview when `isFullGraphScene`. Otherwise `getOverviewScene()` must finish (slow at 40k). Policy C never became full-graph → minimap waited on a heavy secondary solve (or never painted usefully). Policy A makes the primary scene full-graph so minimap updates immediately. |

### Vendor

`src/okbay/static/vendor/knowledge-atlas.js` **byte-identical** to CE wiki-view vendor (`md5 8574eaa9…`). No IIFE rebuild required.

### Config before → after

```
BEFORE (Policy C):
  layout: hybrid, corpusSize, maxVisibleNodes: 10000
  // budget defaults → maxAggregates: 40

AFTER (Policy A = CE atlas.js):
  layout: hybrid, corpusSize,
  coreCapacity: corpusSize, maxVisibleNodes: corpusSize,
  budget: { maxNodes: corpusSize, maxAggregates: 0, maxEdges: max(900, edges) }
```

### Follow-ups

- [x] Node type coloring fidelity — Rust `theme.rs` full Switchbay palette (no empty overrides); graph kinds from wiki `type:` via rebuild/`enrich-kinds`; sidebar dots use `CEData.palette`
- [x] Label option buttons + type popup — slim `OkbayAtlasChrome.Controls` → `handle.setLabels`
- [x] Richer file highlight / locate UX — modal Reveal files, `reveal=0|1`, status toast, sources/files list
- [ ] Option-3 kiosk packaging

**Type coloring path:** hot `/api/atlas/data` uses graph node `kind` (fast). After wiki ingest or stale `kind: note`, run `okbay graph rebuild` (full) or `okbay graph enrich-kinds` / `POST /api/atlas/enrich-kinds` (Python) / rebuild graph from wiki. Daemon start already rebuilds in Rust `serve()`.

### Validate (2026-09-11 ~11:29 CEST / Europe/Zurich)

- Chromium title after scene-ready: was `OKBay Atlas · n=40097 a=0 e=123039` (**zero aggregates**); host now omits `a=` / `aggs=` entirely (`OKBay Atlas · n=… e=…`).
- Screenshot: `/workspace/omarchy-vm/logs/screen-atlas-ce-no-aggs.png` (QEMU screendump; grim failed under Hyprland 0.56 display capture).
- Visual: individual colored nodes only (no numbered type bubbles); **minimap visible** bottom-right; dense force core still somewhat rectangular/blocky (full-graph force equilibrium + fit — not the old squircle+aggregate rim). Cosmological aggregate shells gone.
- Local engine check (2k synth): Policy C-ish → aggregates > 0; Policy A → aggregates == 0 / no shell nodes (vitest, ephemeral).
- TCG cold layout for Biocure Policy A took ~9–10 minutes before `scene-ready`.
- Vendor IIFE unchanged (byte-identical to CE).

## Chrome gaps fix (2026-09-11 evening)

- **Invisible labels root cause:** controls existed in DOM (top-right, z-index 5) but were low-contrast against the dense graph and easy to miss / crop under Chromium `--app` chrome. Not behind canvas. Fix: CE bottom-left placement, solid `bg-elev`, accent state text, z-index 20, remount after `KnowledgeAtlas.mount`.
- **Expand/collapse-all:** CE `sidebar-toggle-all` ported next to Fuse search.
- **Search → highlight:** Sidebar `onHighlight` → `engine.select(ids)` + `focus(first)` while typing; row click focuses too.
- **Classic hide:** `MIN_ATLAS_PAGES = 360`. Okbay has no classic viewer; `#viewer-mode` remains `hidden`. If classic is added later for small graphs, only show the chooser when `pageCount ≤ 360`.
