#!/usr/bin/env bash
# OKBay full-product opener for Hyprland / Omarchy guests (Mac Mini + Try Omarchy).
# Super+Shift+K → this script (see contrib/hypr-bindings.lua).
# Super+Ctrl+K is the Mac-host alt when the host steals Super+Shift+K.
#
# Opens: okstratr panel summon + best-effort Herdr desk start + Atlas opener.
# Super+Shift+O remains okstratr-only (okstratr contrib/hypr-bindings.lua).
set -u
export OMARCHY_PATH="${OMARCHY_PATH:-/usr/share/omarchy}"
export PATH="${HOME}/.local/bin:/usr/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Import Wayland/Display from systemd user session when launched outside the desktop.
if [[ -z "${WAYLAND_DISPLAY:-}" || -z "${XDG_RUNTIME_DIR:-}" ]]; then
  if command -v systemctl >/dev/null 2>&1; then
    while IFS= read -r line; do
      case "$line" in
        WAYLAND_DISPLAY=*|XDG_RUNTIME_DIR=*|DISPLAY=*|HYPRLAND_INSTANCE_SIGNATURE=*|DBUS_SESSION_BUS_ADDRESS=*)
          export "$line"
          ;;
      esac
    done < <(systemctl --user show-environment 2>/dev/null || true)
  fi
fi

# 1) Okstratr FloatingWindow panel (native toplevel).
if command -v omarchy-shell >/dev/null 2>&1; then
  omarchy-shell -q shell summon benjsmith.okstratr '{"surface":"panel"}' >/dev/null 2>&1 || true
fi

# 2) Best-effort Herdr desk start / launch (daemon may be down; never fail the chord).
OKSTRATR_URL="${OKSTRATR_URL:-http://127.0.0.1:8767}"
if command -v curl >/dev/null 2>&1; then
  curl -fsS -m 2 -X POST "${OKSTRATR_URL}/api/herdr/launch" \
    -H 'Content-Type: application/json' \
    -d '{}' >/dev/null 2>&1 \
  || curl -fsS -m 2 -X POST "${OKSTRATR_URL}/api/desk/start" \
    -H 'Content-Type: application/json' \
    -d '{"kind":"auto","drive_herdr":true}' >/dev/null 2>&1 \
  || true
fi

# 3) Atlas Chromium focus-or-launch (same helper as the former K-only bind).
ATLAS_HELPER=""
for candidate in \
  "${SCRIPT_DIR}/okbay-open-atlas.sh" \
  "${HOME}/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-atlas.sh" \
  "${HOME}/.local/bin/okbay-open-atlas.sh"
do
  if [[ -x "$candidate" ]]; then
    ATLAS_HELPER="$candidate"
    break
  fi
done

if [[ -n "$ATLAS_HELPER" ]]; then
  exec "$ATLAS_HELPER" "$@"
fi

echo "okbay-open-full-product: okbay-open-atlas.sh not found" >&2
exit 0
