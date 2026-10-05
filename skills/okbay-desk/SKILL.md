---
name: okbay-desk
description: >-
  Thin alias of the canonical okstratr desk skill. Same serve/observer
  lifecycle and desk orchestration — not a second desk product. Prefer /okstratr.
---

# okbay-desk (alias → okstratr)

**Canonical skill: `okstratr` (`/okstratr`).** This entry is a thin alias only.

When this skill is invoked (`/okbay-desk` or auto-loaded as okbay-desk), behave
exactly as **okstratr** — same entrypoint, no parallel desk product:

## Lifecycle (consent-first)

```
/okstratr status
/okstratr start
/okstratr restart
/okstratr shutdown
```

CLI equivalents: `okstratr status|doctor|start|restart|shutdown` (use `--yes` only for automation).

## Desk orchestration

Use **okstratr** desk commands (not a separate okbay desk product path):

```
okstratr desk start <kind> …
okstratr desk stop|dismiss|status|…
```

Kinds and observer panel follow okstratr (`http://127.0.0.1:8767/observer/`).

## Do not

- Do not invent a third desk product or duplicate okstratr logic here.
- Do not silently daemonize serve without consent on the skill path.

`okbay-ask` remains separate (Atlas/wiki Q&A only).
