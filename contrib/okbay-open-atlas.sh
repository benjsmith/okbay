#!/usr/bin/env bash
# Bulletproof OKBay Atlas opener for Hyprland / Omarchy guests.
# Super+Shift+K → this script (see contrib/hypr-bindings.lua).
# OMARCHY_PATH is required by omarchy-shell; SSH/some launches miss it.
#
# Super+Shift+K must open exactly ONE Atlas Chromium. Do not also
# omarchy-shell summon here: Panel.openAtlasWindow races this launcher
# and produces a second window. Menu/extension paths may still summon.
#
# Frameless / option-3 packaging:
#   Chromium --app= strips browser chrome; --class=OkbayAtlas lets Hyprland
#   windowrules float/fullscreen/special-workspace (see hypr-bindings.lua).
# OKBAY_ATLAS_TILED=1 (full-product): never --start-fullscreen; replace any
# existing Atlas process so a prior solo fullscreen window cannot stick.
export OMARCHY_PATH="${OMARCHY_PATH:-/usr/share/omarchy}"
export PATH="${HOME}/.local/bin:/usr/bin:${PATH}"

# Optional first arg overrides URL (also OKBAY_ATLAS_URL). Used by bar Library click.
if [[ "${1:-}" == http://* || "${1:-}" == https://* ]]; then
  ATLAS_URL="$1"
  shift
else
  ATLAS_URL="${OKBAY_ATLAS_URL:-http://127.0.0.1:8766/atlas}"
fi
ATLAS_MATCH='chromium.*(8766/atlas|OkbayAtlas|--class=OkbayAtlas|chrome-.*atlas)'
ATLAS_CLASS="${OKBAY_ATLAS_CLASS:-OkbayAtlas}"

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
  addr="$(hyprctl clients -j 2>/dev/null | ATLAS_CLASS="${ATLAS_CLASS}" python3 -c '
import json, os, sys
want = (os.environ.get("ATLAS_CLASS") or "OkbayAtlas").lower()
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
    if want and want in classes.lower():
        print(c.get("address") or "")
        sys.exit(0)
    if want and want in initial_class.lower():
        print(c.get("address") or "")
        sys.exit(0)
    if "8766/atlas" in title.lower() or "8766/atlas" in initial.lower():
        print(c.get("address") or "")
        sys.exit(0)
    # Omarchy Chromium often ignores --class=OkbayAtlas → chrome-127.0.0.1__atlas-Default
    if classes.lower().startswith("chrome-") or initial_class.lower().startswith("chrome-"):
        chrome_blob = (classes + " " + initial_class + " " + title + " " + initial).lower()
        if "atlas" in chrome_blob or "8766" in chrome_blob:
            print(c.get("address") or "")
            sys.exit(0)
    if ("chromium" in blob or "chrome" in blob) and ("okbay" in title.lower() or "atlas" in title.lower() or "8766" in blob):
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
  # --app= : frameless Chromium app window (no tab strip / omnibox).
  # --class= / --name= : keep OkbayAtlas for Hypr windowrules when Chromium
  # honours them. Under Omarchy Wayland, Chromium often ignores --class and
  # reports app_id chrome-127.0.0.1__atlas-Default — arrange/classify must
  # match that fallback (see okbay-arrange-full-product.py).
  # Dedicated user-data-dir keeps Atlas cookies/profile separate from default.
  # OKBAY_ATLAS_TILED=1 (full-product 2x2): skip --start-fullscreen so the
  # pane can sit in a workspace grid instead of covering the prior desktop.
  local profile="${OKBAY_ATLAS_PROFILE:-${HOME}/.local/share/okbay/chromium-atlas}"
  mkdir -p "$profile" 2>/dev/null || true
  local flags=(
    --ozone-platform=wayland
    --class="${ATLAS_CLASS}"
    --name="${ATLAS_CLASS}"
    --user-data-dir="${profile}"
    --app="${ATLAS_URL}"
  )
  if [[ "${OKBAY_ATLAS_TILED:-0}" != "1" ]]; then
    flags+=(--start-fullscreen)
  fi
  if command -v uwsm-app >/dev/null 2>&1; then
    nohup uwsm-app -- chromium "${flags[@]}" \
      >/tmp/okbay-atlas-chrome.log 2>&1 &
  else
    nohup chromium "${flags[@]}" \
      >/tmp/okbay-atlas-chrome.log 2>&1 &
  fi
}

unset_atlas_fullscreen() {
  command -v hyprctl >/dev/null 2>&1 || return 0
  command -v python3 >/dev/null 2>&1 || return 0
  hyprctl clients -j 2>/dev/null | ATLAS_CLASS="${ATLAS_CLASS}" python3 -c '
import json, os, subprocess, sys
want = (os.environ.get("ATLAS_CLASS") or "OkbayAtlas").lower()
try:
    clients = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for c in clients:
    cls = c.get("class")
    classes = " ".join(str(x) for x in cls) if isinstance(cls, list) else str(cls or "")
    blob = " ".join([
        classes,
        str(c.get("initialClass") or ""),
        str(c.get("title") or ""),
        str(c.get("initialTitle") or ""),
    ]).lower()
    if (
        want not in blob
        and "8766/atlas" not in blob
        and not ("atlas" in blob and ("chromium" in blob or "chrome" in blob))
        and not (blob.startswith("chrome-") and ("atlas" in blob or "8766" in blob))
        and not ("chrome-" in blob and ("atlas" in blob or "8766" in blob))
    ):
        continue
    addr = c.get("address") or ""
    if not addr:
        continue
    subprocess.run(["hyprctl", "dispatch", "focuswindow", f"address:{addr}"], capture_output=True)
    subprocess.run(["hyprctl", "dispatch", "fullscreen", "0"], capture_output=True)
    subprocess.run(["hyprctl", "dispatch", "fullscreen", "0", f"address:{addr}"], capture_output=True)
    subprocess.run(["hyprctl", "dispatch", "fullscreenstate", "0", "0"], capture_output=True)
' 2>/dev/null || true
}

ensure_atlas_chromium() {
  # Full-product / tiled: NEVER reuse a leftover --start-fullscreen Atlas.
  # Kill and relaunch without --start-fullscreen, then force hyprctl fullscreen 0.
  if [[ "${OKBAY_ATLAS_TILED:-0}" == "1" ]]; then
    if [[ "$(count_atlas_chromium)" -gt 0 ]]; then
      pkill -f "${ATLAS_MATCH}" 2>/dev/null || true
      sleep 0.25
    fi
    launch_atlas_chromium
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
      sleep 0.15
      if focus_atlas_window; then
        unset_atlas_fullscreen
        return 0
      fi
    done
    unset_atlas_fullscreen
    return 0
  fi

  # Solo Atlas: prefer focus existing; else launch once (may use --start-fullscreen).
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

# Hash routes (e.g. #view=library) need a fresh --app= URL; focus alone keeps the old hash.
if [[ "${ATLAS_URL}" == *#* ]]; then
  if [[ "$(count_atlas_chromium)" -gt 0 ]]; then
    pkill -f "${ATLAS_MATCH}" 2>/dev/null || true
    sleep 0.2
  fi
  launch_atlas_chromium
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.15
    if focus_atlas_window; then
      [[ "${OKBAY_ATLAS_TILED:-0}" == "1" ]] && unset_atlas_fullscreen
      exit 0
    fi
  done
  [[ "${OKBAY_ATLAS_TILED:-0}" == "1" ]] && unset_atlas_fullscreen
  exit 0
fi

ensure_atlas_chromium
exit 0
