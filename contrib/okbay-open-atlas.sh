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
# Seeded dedicated profile + --no-first-run skips Additional Terms of Service
# (empty class until past ToS breaks full-product classify).
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
    if classes.lower().startswith("chrome-") or initial_class.lower().startswith("chrome-"):
        chrome_blob = (classes + " " + initial_class + " " + title + " " + initial).lower()
        if "atlas" in chrome_blob or "8766" in chrome_blob:
            print(c.get("address") or "")
            sys.exit(0)
    if ("chromium" in blob or "chrome" in blob) and ("okbay" in title.lower() or "atlas" in title.lower() or "8766" in blob):
        print(c.get("address") or "")
        sys.exit(0)
    if not classes.strip() and not initial_class.strip():
        tblob = (title + " " + initial).lower()
        if (
            "terms of service" in tblob
            or "additional terms" in tblob
            or "8766" in tblob
            or "atlas" in tblob
            or "127.0.0.1" in tblob
            or "okbay" in tblob
        ):
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

seed_atlas_profile() {
  # Pre-accept first-run / Additional Terms of Service for a fresh dedicated profile.
  local profile="$1"
  mkdir -p "${profile}/Default" 2>/dev/null || true
  : >"${profile}/First Run" 2>/dev/null || true
  if [[ ! -f "${profile}/Local State" ]]; then
    cat >"${profile}/Local State" <<'JSON'
{
  "browser": {
    "enabled_labs_experiments": [],
    "has_seen_welcome_page": true
  },
  "profile": {
    "info_cache": {
      "Default": {
        "active_time": 1.0,
        "is_using_default_name": true,
        "name": "Default"
      }
    },
    "last_used": "Default",
    "last_active_profiles": ["Default"]
  },
  "user_experience_metrics": {
    "client_id2": "okbay-atlas-seed"
  }
}
JSON
  fi
  if [[ ! -f "${profile}/Default/Preferences" ]]; then
    cat >"${profile}/Default/Preferences" <<'JSON'
{
  "browser": {
    "check_default_browser": false,
    "has_seen_welcome_page": true,
    "custom_chrome_frame": false
  },
  "distribution": {
    "import_bookmarks": false,
    "import_history": false,
    "import_search_engine": false,
    "make_chrome_default_for_user": false,
    "require_eula": false,
    "show_welcome_page": false,
    "skip_first_run_ui": true,
    "suppress_first_run_default_browser_prompt": true
  },
  "profile": {
    "default_content_setting_values": {},
    "exit_type": "Normal",
    "exited_cleanly": true
  }
}
JSON
  else
    command -v python3 >/dev/null 2>&1 || return 0
    python3 - "$profile/Default/Preferences" <<'PYSEED' 2>/dev/null || true
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    data = json.loads(p.read_text())
except Exception:
    raise SystemExit(0)
browser = data.setdefault("browser", {})
browser["check_default_browser"] = False
browser["has_seen_welcome_page"] = True
dist = data.setdefault("distribution", {})
dist.update({
    "require_eula": False,
    "show_welcome_page": False,
    "skip_first_run_ui": True,
    "suppress_first_run_default_browser_prompt": True,
    "make_chrome_default_for_user": False,
})
prof = data.setdefault("profile", {})
prof["exit_type"] = "Normal"
prof["exited_cleanly"] = True
p.write_text(json.dumps(data, indent=2))
PYSEED
  fi
}

atlas_window_is_tos() {
  command -v hyprctl >/dev/null 2>&1 || return 1
  command -v python3 >/dev/null 2>&1 || return 1
  hyprctl clients -j 2>/dev/null | python3 -c '
import json,sys
try:
    clients=json.load(sys.stdin)
except Exception:
    raise SystemExit(1)
for c in clients:
    title=(c.get("title") or "")
    initial=(c.get("initialTitle") or "")
    blob=(title+" "+initial).lower()
    if "terms of service" in blob or "additional terms" in blob:
        raise SystemExit(0)
raise SystemExit(1)
' 2>/dev/null
}

launch_atlas_chromium() {
  # Seed + --no-first-run avoids ToS empty-class classify miss.
  # OKBAY_ATLAS_USE_DEFAULT_PROFILE=1 skips --user-data-dir (ToS fallback).
  # OKBAY_ATLAS_TILED=1 skips --start-fullscreen for 2x2 grid.
  local profile="${OKBAY_ATLAS_PROFILE:-${HOME}/.local/share/okbay/chromium-atlas}"
  local flags=(
    --ozone-platform=wayland
    --class="${ATLAS_CLASS}"
    --name="${ATLAS_CLASS}"
    --no-first-run
    --no-default-browser-check
    --disable-features=TranslateUI
    --app="${ATLAS_URL}"
  )
  if [[ "${OKBAY_ATLAS_USE_DEFAULT_PROFILE:-0}" != "1" ]]; then
    seed_atlas_profile "$profile"
    flags+=(--user-data-dir="${profile}")
  else
    local def="${HOME}/.config/chromium"
    mkdir -p "${def}/Default" 2>/dev/null || true
    [[ -f "${def}/First Run" ]] || : >"${def}/First Run" 2>/dev/null || true
  fi
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
        and not (("terms of service" in blob or "additional terms" in blob) and not classes.strip())
    ):
        continue
    addr = c.get("address") or ""
    if not addr:
        continue
    fs = c.get("fullscreen") or 0
    try:
        fs_on = bool(int(fs))
    except Exception:
        fs_on = bool(fs)
    # Omarchy 0.56 Lua: mode=0 ENTERS fullscreen; toggle OFF with mode="fullscreen"
    subprocess.run(["hyprctl", "dispatch", f'hl.dsp.focus({{ window = "address:{addr}" }})'], capture_output=True)
    if fs_on:
        subprocess.run(
            ["hyprctl", "dispatch", 'hl.dsp.window.fullscreen({ mode = "fullscreen" })'],
            capture_output=True,
        )
' 2>/dev/null || true
}

wait_atlas_past_tos() {
  # Wait until Atlas window exists and is no longer on Additional Terms title.
  local i
  for i in $(seq 1 "${1:-40}"); do
    sleep 0.2
    if focus_atlas_window; then
      if atlas_window_is_tos; then
        continue
      fi
      return 0
    fi
  done
  focus_atlas_window || true
  if atlas_window_is_tos; then
    return 1
  fi
  return 0
}

ensure_atlas_chromium() {
  # Full-product / tiled: NEVER reuse a leftover --start-fullscreen Atlas.
  if [[ "${OKBAY_ATLAS_TILED:-0}" == "1" ]]; then
    if [[ "$(count_atlas_chromium)" -gt 0 ]]; then
      pkill -f "${ATLAS_MATCH}" 2>/dev/null || true
      sleep 0.25
    fi
    export OKBAY_ATLAS_USE_DEFAULT_PROFILE="${OKBAY_ATLAS_USE_DEFAULT_PROFILE:-0}"
    launch_atlas_chromium
    if wait_atlas_past_tos 40; then
      unset_atlas_fullscreen
      return 0
    fi
    if [[ "${OKBAY_ATLAS_USE_DEFAULT_PROFILE}" != "1" ]]; then
      echo "okbay-open-atlas: ToS stuck on dedicated profile; falling back to default profile" >>/tmp/okbay-atlas-chrome.log 2>/dev/null || true
      pkill -f "${ATLAS_MATCH}" 2>/dev/null || true
      sleep 0.3
      OKBAY_ATLAS_USE_DEFAULT_PROFILE=1 launch_atlas_chromium
      wait_atlas_past_tos 30 || true
    fi
    unset_atlas_fullscreen
    return 0
  fi

  if focus_atlas_window; then
    return 0
  fi
  if [[ "$(count_atlas_chromium)" -gt 0 ]]; then
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

