# Atlas host views shell

OKBay Atlas (option-3 Chromium host) is a **workspace-scoped views shell**.
The bottom `view:` control opens a popup (same pattern as `types:`) listing:

| View | Role |
|------|------|
| **Atlas** | KnowledgeAtlas canvas + left sidebar search |
| **Viewer** | Unified page/source renderer; sticky selection; back/forward |
| **Table** | Tabular browse (title / kind / type) |
| **Library** | Sources / figures / tables |
| **Projects** | Project pages |
| **Reviews** | Pending reviews only (hidden when empty); Accept All |

Dynamic views (Herdr / okstratr) appear below the built-ins after
`POST /api/views` or MCP `okbay_publish_view`. HTML is stored under
`<workspace>/.okbay/views/` and served at `/views/<id>` inside a sandboxed
iframe (`sandbox` + CSP). See `skills/okbay-views/SKILL.md`.

## Routing

- `#view=atlas`
- `#view=viewer&page=<stem>`
- `#view=table` / `library` / `projects` / `reviews`
- `#view=<dynamic-id>`

Legacy `#page=<stem>` opens Viewer for that page.

## Viewer behaviour

- Double-click graph node or list row → Viewer (not cleared by empty canvas clicks).
- Selecting another doc replaces the sticky selection.
- Source chips on a wiki page switch Viewer to source mode in-place.
- ← / → in the Viewer chrome walk a history stack.

## Stem index warm

`wiki.warm_stem_index()` builds the stem→path index at serve start (daemon
thread) and on workspace switch. Optional persist: `.okbay/stem-index.json`.
