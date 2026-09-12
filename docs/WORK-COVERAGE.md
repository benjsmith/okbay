# Work coverage

OKBay’s default experience is **magical coverage of `~/Work`**, not “you must open a named corpus”.

**Biocure** is the **active demo workspace** we use now (hub vault/wiki + graph). It is not an optional opt-in product surface — it is the current demo.

**Optional** = creating **additional focused workspaces** (topic-scoped) when you do not want “all my work” in one wiki. Split Work subfolders out of the default coverage into their own watch list.

## Roots

| Concept | Default | Override |
| --- | --- | --- |
| **Coverage root** (watched docs/data) | `~/Work` | `OKBAY_WORK_ROOT` or `work_root` in config |
| **Hub workspace** (vault + wiki + graph) | `~/Work/okbay` | `OKBAY_WORKSPACE` / `okbay setup --workspace` |
| **Demo workspace** (Biocure) | active demo hub | `okbay workspace use biocure` |
| **Focused workspaces** (optional) | none | `okbay workspace split` |

Config file: `~/.config/okbay/coverage.toml`

```toml
work_root = "/home/you/Work"
opt_out = ["/home/you/Work/secrets", "**/hr-private/**", "/home/you/Work/biocure"]
active_workspace = "biocure"

[workspaces]
okbay = "/home/you/Work/okbay"
biocure = "/home/you/Work/biocure-wiki"

[watch_roots]
biocure = ["/home/you/Work/biocure"]
```

### Smooth path: all-Work → focused split

Start with magical coverage of all of `~/Work`. When a topic should have its own wiki:

```sh
okbay workspace split biocure ~/Work/biocure
# or: okbay coverage split biocure ~/Work/biocure
okbay workspace use biocure
okbay workspace list
```

That command:

1. Creates/registers a workspace hub (`~/Work/<name>-wiki` by default) with vault/wiki layout
2. Sets the new workspace **watch list** to the given Work subfolder(s)
3. Adds those folders to the default Work **`opt_out`** list (excluded from all-Work coverage)
4. Persists both sides in `coverage.toml` (idempotent if re-run)

## Opt-out

Sensitive folders never enter the ingest pipeline (independent of splits):

```sh
okbay coverage opt-out ~/Work/payroll
okbay coverage opt-in ~/Work/payroll
okbay coverage status
```

Globs are allowed in `opt_out`. Prefix paths are treated as directory trees. Paths opted out by `workspace split` stay on the focused workspace watch list even though they are excluded from default Work coverage.

## Privacy + financial gate

Before a file is copied into the vault, `privacy_gate` scans it:

1. **GDPR-likely PII** — wraps curiosity-merge `find_gdpr_likely_pii` when `/workspace/curiosity-merge/scripts/preflight.py` (or `OKBAY_CURIOSITY_PREFLIGHT`) is importable; otherwise a stdlib regex fallback (email, E.164 phone, SSN, IBAN, payment-card-shaped).
2. **Financial / pricing** — currency amounts, account numbers, and commercial keywords (invoice, ARR, burn rate, …), severity `warn`.

If findings need confirmation and `confirm` is false, ingest returns:

```json
{"ok": false, "needs_confirm": true, "findings": [...]}
```

without copying. UI/popup should `POST /api/privacy/scan` then `POST /api/ingest` with `"confirm": true`. Headless callers pass `--confirm` / `confirm=True` after review. The gate does **not** block forever waiting for interactive input.

```sh
okbay privacy ~/Work/notes/pricing.md
okbay ingest ~/Work/notes/pricing.md --confirm
```

## Efficient watcher

```sh
okbay watch once
okbay watch serve --interval 3 --debounce 2.5
```

- Prefer **watchdog** (inotify) when installed; else periodic **mtime index** in `~/.local/state/okbay/watch_mtime.sqlite`.
- Debounce 2–5s; batch `MAX_FILES_PER_TICK`; skip opt-outs, `.git` trees, huge binaries, `node_modules`, etc.
- No constant full-tree content rescans — only mtime/size deltas (or event paths).
- Default active hub watches `work_root` (minus opt-outs). A focused workspace with `[watch_roots]` watches those folders only.

## Code vs docs

Git repositories under the coverage root are **not** vault-ingested. The watcher records a lightweight `kind: decision` wiki stub (+ blackboard breadcrumb) via `code_policy.note_repo_change`. Source dumps never land in the vault.

Exception: files already under the active hub’s `vault/` (explicit drops) may ingest even if the hub checkout itself is a git repo.

## HTTP

- `POST /api/privacy/scan` — `{ "path": "..." }` → scan result
- `POST /api/ingest` — `{ "path": "...", "confirm": true|false }`
- `POST /api/coverage` — coverage status snapshot
- `POST /api/workspace/split` — `{ "name": "biocure", "paths": ["~/Work/biocure"], "hub": "..."? }`
