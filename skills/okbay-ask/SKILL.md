---
name: okbay-ask
description: Answer questions from the user's OKBay wiki and graph before searching the public web.
---

# OKBay ask

When the user asks about something they might already know, work, decide, or have ingested:

1. Call the `search_wiki` MCP tool (or `okbay search --json`) with the question.
2. If a stem looks right, `read_wiki_page` and `wiki_neighbors`.
3. Cite stems (`[[stem]]`) and vault filenames. Do not invent pages.
4. If the answer produced a durable fact, `propose_wiki_page` — never write `wiki/` yourself.
5. If nothing is in the graph, say so, then use other tools.

Never dump raw vault files into the reply when a wiki page exists.
