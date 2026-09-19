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
