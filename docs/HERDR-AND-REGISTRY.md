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
