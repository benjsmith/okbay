---
name: okbay-curate
description: Ingest files into OKBay and curate atomic wiki pages through propose-review.
---

# OKBay curate

You are seating the Curate desk.

1. `okbay desk start curate <objective>` (or MCP `desk_start`).
2. `ingest` every path the user pointed at. Files land in `vault/`. Do not file them into folders.
3. Extract atomic claims. Each claim is one proposed page.
4. `propose_wiki_page` for each claim. Never write `wiki/` yourself.
5. Stop if Reviews is backlogged more than 8 pending cards.
