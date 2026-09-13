#!/usr/bin/env bash
# Bulletproof OKBay Atlas opener for Hyprland / Omarchy guests.
# Super+Shift+K → this script (see contrib/hypr-bindings.lua).
# OMARCHY_PATH is required by omarchy-shell; SSH/some launches miss it.
#
# Super+Shift+K must open exactly ONE Atlas Chromium. Do not also
# omarchy-shell summon here: Panel.openAtlasWindow races this launcher
# and produces a second window. Menu/extension paths may still summon.
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

count_atlas_chromium() {
  pgrep -f "${ATLAS_MATCH}" 2>/dev/null | wc -l | tr -d " "
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
  # Prefer focus existing Atlas Chromium; else launch once.
  if focus_atlas_window; then
    return 0
  fi
  if [[ "$(count_atlas_chromium)" -gt 0 ]]; then
    # Process up but window not focusable yet — wait briefly, then focus or replace.
    for _ in 1 2 3 4 5 6 7 8; do
      sleep 0.15
      if focus_atlas_window; then
        return 0
      fi
    done
    pkill -f "${ATLAS_MATCH}" 2>/dev/null || true
    sleep 0.2
  fi
  launch_atlas_chromium
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.15
    focus_atlas_window && return 0
  done
  return 0
}

# Optional plugin wake only when explicitly requested (menu paths).
# Default off: summon + Chromium was opening two Atlas windows on Super+Shift+K.
if [[ "${OKBAY_DO_SUMMON:-0}" == "1" ]] && command -v omarchy-shell >/dev/null 2>&1; then
  omarchy-shell -q shell summon benjsmith.okbay '{"surface":"atlas"}' >/dev/null 2>&1 || true
  for _ in 1 2 3 4 5 6 7 8; do
    if focus_atlas_window; then
      exit 0
    fi
    sleep 0.12
  done
fi

ensure_atlas_chromium
exit 0
