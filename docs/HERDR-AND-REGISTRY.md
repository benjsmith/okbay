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
okstratr harness list
okstratr harness detect
okstratr harness enable <id>
okstratr harness disable <id>
```


## Thin client pattern (Switchbay precedent; okbay follow-up)

Switchbay exposes path-native okstratr façades so shells/UI never hard-code
embed upstreams:

| Concern | Switchbay route | Upstream SSOT |
|---------|-----------------|---------------|
| Host notify (C2) | `POST /api/okstratr/host-notify` | okstratr → rail |
| Harness registry | `GET/POST /api/okstratr/harness…` | okstratr `harnesses.toml` |
| Same-origin embed | `/embed/okstratr/api/harness…` | loopback :8767 |

okbay should use the **same thin-client shape** when wiring settings:

- Prefer a local `/api/okstratr/harness` (and enable/disable/set) that
  calls okstratr with `X-Okstratr-Host: okbay`.
- Browser may use proxied `/embed/okstratr/…` when that proxy exists.
- **Do not** invent an okbay-side allowlist file.
- Full okbay settings UI for harness toggles is a follow-up; until then
  CLI (`okstratr harness …`) and/or Switchbay Settings remain the write path.

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

