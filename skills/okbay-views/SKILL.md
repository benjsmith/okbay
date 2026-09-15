---
name: okbay-views
description: Publish and open workspace-scoped Atlas host views (Herdr/okstratr decks).
---

# OKBay views

Atlas host is a **views shell**. Built-ins: Atlas, Viewer, Table, Library, Projects, Reviews (when pending). Herdr/okstratr can JIT-publish sandboxed HTML decks.

## MCP tools

- `okbay_list_views` — built-in + dynamic views for the active workspace
- `okbay_publish_view` — `{id, title, html|url, ephemeral?}` → persists under `<workspace>/.okbay/views/`
- `okbay_open_view` — returns `http://127.0.0.1:8766/atlas#view=<id>&page=…`

## HTTP

- `GET /api/views`
- `POST /api/views` body `{id, title, html|url, ephemeral?}`
- `DELETE /api/views/:id`
- `GET /views/:id` — CSP-restricted HTML for sandboxed iframe

## Example

```json
{
  "id": "deck-q3",
  "title": "Q3 strategy",
  "html": "<!doctype html><h1>Q3</h1><p>…</p>",
  "ephemeral": true
}
```

Then open `#view=deck-q3` in the Atlas Chromium host (Super+Shift+K).
