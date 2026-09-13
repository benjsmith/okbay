#!/usr/bin/env bash
# Bulletproof OKBay Atlas opener for Hyprland / Omarchy guests.
# Super+Shift+K → this script (see contrib/hypr-bindings.lua).
# OMARCHY_PATH is required by omarchy-shell; SSH/some launches miss it.
#
# Always open/focus Atlas via Chromium. omarchy-shell summon often succeeds
# without re-calling Panel.open()/openAtlasWindow() when the plugin is already
# loaded — so summon success must NOT short-circuit Chromium.
export OMARCHY_PATH="${OMARCHY_PATH:-/usr/share/omarchy}"
export PATH="${HOME}/.local/bin:/usr/bin:${PATH}"

ATLAS_URL="${OKBAY_ATLAS_URL:-http://127.0.0.1:8766/atlas}"
ATLAS_MATCH='chromium.*8766/atlas'

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

focus_atlas_window() {
  command -v hyprctl >/dev/null 2>&1 || return 1
  local addr
  addr="$(hyprctl clients -j 2>/dev/null | python3 -c '
import json, sys
try:
    clients = json.load(sys.stdin)
except Exception:
    sys.exit(1)
for c in clients:
    title = str(c.get("title") or "")
    initial = str(c.get("initialTitle") or "")
    cls = c.get("class")
    if isinstance(cls, list):
        classes = " ".join(str(x) for x in cls)
    else:
        classes = str(cls or "")
    initial_class = str(c.get("initialClass") or "")
    blob = (classes + " " + title + " " + initial + " " + initial_class).lower()
    if "8766/atlas" in title.lower() or "8766/atlas" in initial.lower():
        print(c.get("address") or "")
        sys.exit(0)
    if "chromium" in blob and ("okbay" in title.lower() or "atlas" in title.lower()):
        print(c.get("address") or "")
        sys.exit(0)
sys.exit(1)
' 2>/dev/null || true)"
  [[ -n "${addr:-}" ]] || return 1
  hyprctl dispatch focuswindow "address:${addr}" >/dev/null 2>&1
}

launch_atlas_chromium() {
  if command -v uwsm-app >/dev/null 2>&1; then
    nohup uwsm-app -- chromium --ozone-platform=wayland --app="${ATLAS_URL}" --start-fullscreen \
      >/tmp/okbay-atlas-chrome.log 2>&1 &
  else
    nohup chromium --ozone-platform=wayland --app="${ATLAS_URL}" --start-fullscreen \
      >/tmp/okbay-atlas-chrome.log 2>&1 &
  fi
}

ensure_atlas_chromium() {
  # Prefer focus existing Atlas Chromium; else launch. Only pkill when stale
  # (process matches but no focusable window).
  if pgrep -f "${ATLAS_MATCH}" >/dev/null 2>&1; then
    if focus_atlas_window; then
      return 0
    fi
    pkill -f "${ATLAS_MATCH}" 2>/dev/null || true
    sleep 0.15
  fi
  launch_atlas_chromium
}

# Best-effort summon (plugin wake / Panel path) — never treat success as "done".
# Panel/Overlay call this script with OKBAY_SKIP_SUMMON=1 to avoid summon→open recursion.
if [[ -z "${OKBAY_SKIP_SUMMON:-}" ]] && command -v omarchy-shell >/dev/null 2>&1; then
  omarchy-shell -q shell summon benjsmith.okbay '{"surface":"atlas"}' >/dev/null 2>&1 || true
  # Give Panel a brief window to open Chromium when summon actually reaches openAtlasWindow.
  for _ in 1 2 3 4 5; do
    if pgrep -f "${ATLAS_MATCH}" >/dev/null 2>&1; then
      focus_atlas_window && exit 0
      break
    fi
    sleep 0.12
  done
fi

ensure_atlas_chromium
exit 0
