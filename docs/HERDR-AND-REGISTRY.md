# Herdr + okstratr registry (okbay)

See **[SKILL-SHELL-INVENTORY.md](./SKILL-SHELL-INVENTORY.md)** §D–E for the Phase 5a contracts.

## Herdr — okbay / Omarchy only

- Mac Switchbay seats agents via **direct** harness CLIs (no Herdr).
- Omarchy + okbay may enable okstratr registry backend `herdr`.
- okbay does not embed Herdr HTML; panes stay Omarchy-native.
- Finite jobs: `okstratr herdr run-ready` (always stop/release).

## Settings → okstratr registry (SSOT)

- okbay settings UIs write **okstratr** harness+model registry only.
- No second allowlist inside okbay.
- Hosted mode (`host=okbay`): okstratr HTML settings pages stay off.

```bash
okbay harness list|enable|disable|set|reload   # preferred (thin client)
okstratr harness list|detect|enable|disable    # upstream CLI still ok
```


## Thin client (Switchbay parity)

okbay mirrors Switchbay ADR-005: a **thin client** over okstratr
`harnesses.toml` — no second allowlist under okbay state.

| Surface | Path / command |
|---------|----------------|
| List | `GET /api/okstratr/harness` · `okbay harness list` |
| Enable | `POST /api/okstratr/harness/enable` `{ "id" }` · `okbay harness enable <id>` |
| Disable | `POST /api/okstratr/harness/disable` `{ "id" }` · `okbay harness disable <id>` |
| Set | `POST /api/okstratr/harness/set` `{ "key", "value" }` · `okbay harness set <key> [value]` |
| Reload | `POST /api/okstratr/harness/reload` · `okbay harness reload` |

Implementation: `okbay.okstratr_harness` posts to
`OKBAY_OKSTRATR_UPSTREAM` (default `http://127.0.0.1:8767`) with
`X-Okstratr-Host: okbay`, loopback-guarded. Responses are normalized
(`ssot: okstratr`) and never invent an allowlist.

```bash
okbay harness list
okbay harness enable grok
okbay harness disable codex
okbay harness set harness.grok.default_model grok-4
okbay harness reload
curl -s http://127.0.0.1:8766/api/okstratr/harness | jq .
```

`okbay status` / `GET /api/status` include a cheap `harness_registry`
pointer (no upstream call). Rich Atlas Settings UI remains a follow-up;
CLI + daemon routes are first-class for bare-adjacent Omarchy users.

Upstream CLI still works: `okstratr harness list|enable|…`.

See Switchbay `docs/ADR-005-okstratr-harness-registry-client.md`.


## Path-native notify (contract C2)

Schedule / desk progress on the okbay path goes to **Herdr only** — not OS notify,
not a second inbox. See skill-shell `CONTRACT-AUTO-START-AND-NOTIFY.md` and okstratr
`ADR-005-host-notify-and-health.md`.

### Flow

1. okstratr emits `okstratr.host_notify` v1.
2. With `OKSTRATR_HOST=okbay` (or `OKSTRATR_HOSTED=okbay`), okstratr POSTs to
   `http://127.0.0.1:8766/api/okstratr/host-notify` by default.
3. Override with `OKSTRATR_HOST_NOTIFY_URL` if needed.
4. okbay validates the envelope and maps it to Herdr stub I/O:
   - Append JSONL → `~/.local/state/okbay/herdr-notify.jsonl`
     (override: `OKBAY_HERDR_NOTIFY_LOG`)
   - Print `herdr: <title+body line>` on stderr for live tails

### CLI

```bash
okbay host-notify '{"type":"okstratr.host_notify","v":1,"kind":"schedule.start",...}'
echo '{...}' | okbay host-notify
```

Herdr (or a future bridge) should **tail** the JSONL; full Herdr ingest API can
replace the stub later without changing the envelope contract.

## Session auto-start (contract C1)

On ``okbay serve`` / daemon start, okbay **always** brings up core skills:

| Skill | Action | Port / URL |
|-------|--------|------------|
| **okstratr** | ``okstratr serve --host 127.0.0.1 --port 8767`` (keep-alive supervisor) | ``http://127.0.0.1:8767`` |
| **CE** | Claim okbay JSON APIs as CE data plane; warm wiki/status | ``http://127.0.0.1:8766`` |

Viewer mutex: when ``viewer_mode=qml``, HTML ``/`` ``/atlas`` ``/views/*`` stay **off**; backends (okstratr + CE APIs) still start. Optional external ``viewer.sh`` only if ``OKBAY_CE_EXTERNAL_VIEWER=1`` **and** HTML mode (side port ``OKBAY_CE_VIEWER_PORT``, default 8090).

### Status

```bash
okbay core-skills status
# or
curl -s http://127.0.0.1:8766/api/core-skills/status
```

C1 shape: ``{ "ce": {...}, "okstratr": {...}, "wiki_build": {...} }``. Also embedded under ``health`` in ``/api/status`` / ``okbay status``.

Env overrides: ``OKBAY_OKSTRATR_UPSTREAM``, ``OKBAY_OKSTRATR_BIN``, ``OKBAY_CE_UPSTREAM``.

