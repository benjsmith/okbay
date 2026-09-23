#!/usr/bin/env bash
# OKBay full-product opener for Hyprland / Omarchy guests (Mac Mini + Try Omarchy).
#
# Live Mac Mini Omarchy guest install path (document for operators):
#   /home/benj/.local/bin/okbay-open-full-product.sh
# Also installed by setup.sh to:
#   ~/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-full-product.sh
#   ~/.local/bin/okbay-open-full-product.sh
#
# Super+Shift+K -> this script (see contrib/hypr-bindings.lua).
# Super+Ctrl+K is the Mac-host alt when the host steals Super+Shift+K.
# Super+Shift+O remains okstratr-only (okstratr contrib/hypr-bindings.lua).
#
# Omarchy-like behaviour (not float-over-current):
#   1) Kill leftover fullscreen Atlas on the *previous* workspace
#   2) Ensure okbayd serves BioCure freeze workspace on :8766
#   3) Switch to a fresh / dedicated Hyprland workspace
#   4) Populate a 2x2 panel split:
#        Top-left:     okbay / Atlas   (class OkbayAtlas)
#        Top-right:    Nautilus        (org.gnome.Nautilus)
#        Bottom-left:  Herdr
#        Bottom-right: okstratr panel
#
# Env knobs:
#   OKBAY_FULL_PRODUCT_WS   workspace target: "next-empty" (default), a number,
#                           or "special:okbay"
#   OKBAY_WORKSPACE         wiki/vault root (default: BioCure freeze tip 5b9711895)
#   OKSTRATR_URL            default http://127.0.0.1:8767
#   OKBAY_ATLAS_URL         Atlas URL for the TL pane
set -u
export OMARCHY_PATH="${OMARCHY_PATH:-/usr/share/omarchy}"
export PATH="${HOME}/.local/bin:/usr/bin:${PATH}"
# Full-product MUST never launch Chromium --start-fullscreen (Ben overlay bug).
export OKBAY_ATLAS_TILED=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="${OKBAY_FULL_PRODUCT_LOG:-/tmp/okbay-full-product.log}"
: >"$LOG" 2>/dev/null || true
log() { printf '%s\n' "$*" >>"$LOG" 2>/dev/null || true; }

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

# Omarchy / SSH: hyprctl needs XDG_RUNTIME_DIR + HYPRLAND_INSTANCE_SIGNATURE.
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if [[ -z "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  if [[ -d "${XDG_RUNTIME_DIR}/hypr" ]]; then
    for _sig in "${XDG_RUNTIME_DIR}/hypr"/*; do
      [[ -d "$_sig" ]] || continue
      export HYPRLAND_INSTANCE_SIGNATURE="$(basename "$_sig")"
      break
    done
  fi
fi
if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  log "HYPRLAND_INSTANCE_SIGNATURE=$HYPRLAND_INSTANCE_SIGNATURE"
fi

# BioCure freeze tip 5b9711895 (not hybrid 76142912). Guest + host well-known paths.
BIOCURE_NAME="biocure-confirm-v1-query-5b9711895"
resolve_biocure_workspace() {
  local cand
  for cand in \
    "${OKBAY_WORKSPACE:-}" \
    "/mnt/mac/Workspaces/${BIOCURE_NAME}" \
    "${HOME}/Workspaces/${BIOCURE_NAME}" \
    "${HOME}/Work/Workspaces/${BIOCURE_NAME}" \
    "${HOME}/Work/${BIOCURE_NAME}"
  do
    [[ -n "$cand" && -d "$cand" ]] || continue
    # Prefer a real workspace root (wiki/ or vault/ or .curator/)
    if [[ -d "$cand/wiki" || -d "$cand/vault" || -d "$cand/.curator" || -d "$cand/.okbay" ]]; then
      printf '%s\n' "$cand"
      return 0
    fi
    printf '%s\n' "$cand"
    return 0
  done
  # Last resort: leave empty so caller can fall back
  return 1
}

# Default OKBAY_WORKSPACE to BioCure freeze when unset / empty.
if [[ -z "${OKBAY_WORKSPACE:-}" ]]; then
  if WS_RESOLVED="$(resolve_biocure_workspace 2>/dev/null)"; then
    export OKBAY_WORKSPACE="$WS_RESOLVED"
  fi
fi
# Still export even when caller set a non-BioCure path — resolve_nautilus uses it first.
if [[ -n "${OKBAY_WORKSPACE:-}" ]]; then
  export OKBAY_WORKSPACE
  log "OKBAY_WORKSPACE=$OKBAY_WORKSPACE"
fi

OKSTRATR_URL="${OKSTRATR_URL:-http://127.0.0.1:8767}"
OKBAY_URL="${OKBAY_URL:-http://127.0.0.1:8766}"

ensure_okstratr_serve() {
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS -m 2 "${OKSTRATR_URL}/api/status" >/dev/null 2>&1 \
      || curl -fsS -m 2 "${OKSTRATR_URL}/health" >/dev/null 2>&1; then
      log "okstratr already up"
      return 0
    fi
  fi
  log "okstratr serve starting"
  if command -v okstratr >/dev/null 2>&1; then
    nohup okstratr serve >>/tmp/okstratr-serve.log 2>&1 &
  elif command -v systemctl >/dev/null 2>&1; then
    systemctl --user start okstratr.service 2>/dev/null \
      || systemctl --user start okstratr-serve.service 2>/dev/null \
      || true
  fi
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.25
    if command -v curl >/dev/null 2>&1; then
      if curl -fsS -m 1 "${OKSTRATR_URL}/api/status" >/dev/null 2>&1 \
        || curl -fsS -m 1 "${OKSTRATR_URL}/health" >/dev/null 2>&1; then
        return 0
      fi
    fi
  done
  log "okstratr serve not confirmed; continuing"
  return 0
}

okbay_status_workspace() {
  command -v curl >/dev/null 2>&1 || return 1
  curl -fsS -m 2 "${OKBAY_URL}/api/status" 2>/dev/null | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(1)
print(d.get("workspace") or "")
' 2>/dev/null
}


ensure_html_viewer() {
  # Full-product Chromium Atlas requires HTML host (qml → /atlas 409).
  mkdir -p "${HOME}/.local/state/okbay" "${HOME}/.config/okbay"
  if command -v okbay >/dev/null 2>&1; then
    okbay viewer set html >>/tmp/okbay-viewer.log 2>&1 \
      || OKBAY_WORKSPACE="${OKBAY_WORKSPACE:-}" okbay viewer set html >>/tmp/okbay-viewer.log 2>&1 \
      || true
  elif [[ -d "${HOME}/src/okbay/src/okbay" ]]; then
    PYTHONPATH="${HOME}/src/okbay/src" python3 -m okbay viewer set html >>/tmp/okbay-viewer.log 2>&1 || true
  else
    printf '%s\n' '{"mode":"html","source":"full-product"}' >"${HOME}/.config/okbay/viewer.json"
  fi
  export OKBAY_VIEWER_MODE=html
  log "viewer mode html (full-product)"
}

ensure_okbay_serve() {
  # Serve BioCure freeze on :8766 before Atlas opens.
  local want="${OKBAY_WORKSPACE:-}"
  if [[ -z "$want" ]]; then
    want="$(resolve_biocure_workspace 2>/dev/null || true)"
  fi
  if [[ -z "$want" || ! -d "$want" ]]; then
    log "okbay workspace missing; skip daemon restart want=${want:-}"
    # Still try to ensure something is listening
    if command -v curl >/dev/null 2>&1; then
      curl -fsS -m 2 "${OKBAY_URL}/health" >/dev/null 2>&1 \
        || curl -fsS -m 2 "${OKBAY_URL}/api/status" >/dev/null 2>&1 \
        && log "okbay already up (unknown workspace)"
    fi
    return 0
  fi
  export OKBAY_WORKSPACE="$want"
  log "ensure okbayd workspace=$want"

  local cur=""
  cur="$(okbay_status_workspace || true)"
  if [[ -n "$cur" ]]; then
    log "okbay current workspace=$cur"
  fi

  local need_restart=0
  if [[ -z "$cur" ]]; then
    need_restart=1
  elif [[ "$cur" != "$want" ]]; then
    # Allow suffix match (symlink /mnt/mac vs ~/Workspaces)
    case "$cur" in
      "$want"|"$want"/*) need_restart=0 ;;
      *"${BIOCURE_NAME}"*)
        # Already on BioCure tip path — ok even if prefix differs
        if [[ "$want" == *"${BIOCURE_NAME}"* ]]; then
          need_restart=0
          log "okbay already on BioCure ($cur)"
        else
          need_restart=1
        fi
        ;;
      *) need_restart=1 ;;
    esac
  fi

  # Reject hybrid tip workspace if accidentally active
  if [[ "$cur" == *"76142912"* ]]; then
    log "okbay on hybrid 76142912 — forcing BioCure freeze restart"
    need_restart=1
  fi

  if [[ "$need_restart" -eq 0 ]]; then
    if curl -fsS -m 2 "${OKBAY_URL}/health" >/dev/null 2>&1 \
      || curl -fsS -m 2 "${OKBAY_URL}/api/status" >/dev/null 2>&1; then
      log "okbay already serving desired workspace"
      ensure_html_viewer
      # Persist via API too (in-process if no env override)
      curl -fsS -m 2 -X POST "${OKBAY_URL}/api/viewer" \
        -H 'Content-Type: application/json' \
        -d '{"mode":"html"}' >/dev/null 2>&1 || true
      # If /atlas still 409 (daemon env stuck on qml), force restart
      atlas_code="$(curl -sS -m 2 -o /dev/null -w '%{http_code}' "${OKBAY_URL}/atlas" 2>/dev/null || echo 000)"
      if [[ "$atlas_code" == "409" ]]; then
        log "atlas still HTTP $atlas_code after viewer set — forcing okbayd restart"
        need_restart=1
      else
        log "atlas HTTP ${atlas_code:-?} (html host ok)"
        return 0
      fi
    else
      need_restart=1
    fi
  fi

  log "okbayd restarting with OKBAY_WORKSPACE=$want"
  mkdir -p "${HOME}/.local/state/okbay" "${HOME}/.config/okbay"
  printf '%s\n' "$want" >"${HOME}/.local/state/okbay/workspace" 2>/dev/null || true
  ensure_html_viewer

  if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop okbayd.service 2>/dev/null || true
  fi
  # Kill stray listeners on 8766
  if command -v fuser >/dev/null 2>&1; then
    fuser -k 8766/tcp >/dev/null 2>&1 || true
  elif command -v lsof >/dev/null 2>&1; then
    lsof -ti :8766 2>/dev/null | xargs -r kill 2>/dev/null || true
  fi
  sleep 0.3

  # NEVER block Super+Shift+K on foreground setup — background only.
  if command -v okbay >/dev/null 2>&1; then
    OKBAY_WORKSPACE="$want" nohup okbay setup --workspace "$want" >>/tmp/okbay-setup.log 2>&1 &
    log "okbay setup backgrounded pid=$!"
  elif [[ -d "${HOME}/src/okbay/src/okbay" ]]; then
    OKBAY_WORKSPACE="$want" PYTHONPATH="${HOME}/src/okbay/src" \
      nohup python3 -m okbay setup --workspace "$want" >>/tmp/okbay-setup.log 2>&1 &
    log "okbay setup (module) backgrounded pid=$!"
  fi

  if command -v systemctl >/dev/null 2>&1 && systemctl --user list-unit-files okbayd.service >/dev/null 2>&1; then
    mkdir -p "${HOME}/.config/systemd/user"
    # Ensure Environment=OKBAY_WORKSPACE + HTML viewer in a drop-in
    mkdir -p "${HOME}/.config/systemd/user/okbayd.service.d"
    cat >"${HOME}/.config/systemd/user/okbayd.service.d/workspace.conf" <<EOF
[Service]
Environment=OKBAY_WORKSPACE=$want
Environment=OKBAY_VIEWER_MODE=html
EOF
    systemctl --user daemon-reload 2>/dev/null || true
    OKBAY_WORKSPACE="$want" OKBAY_VIEWER_MODE=html systemctl --user restart okbayd.service 2>/dev/null \
      || OKBAY_WORKSPACE="$want" OKBAY_VIEWER_MODE=html systemctl --user start okbayd.service 2>/dev/null \
      || true
  fi

  # Fallback: prefer PYTHONPATH module serve when okbayd wrapper fails / health down
  if ! curl -fsS -m 2 "${OKBAY_URL}/health" >/dev/null 2>&1 \
    && ! curl -fsS -m 2 "${OKBAY_URL}/api/status" >/dev/null 2>&1; then
    if [[ -d "${HOME}/src/okbay/src/okbay" ]]; then
      log "okbay serve via PYTHONPATH=~/src/okbay/src python3 -m okbay serve"
      OKBAY_WORKSPACE="$want" OKBAY_VIEWER_MODE=html PYTHONPATH="${HOME}/src/okbay/src" \
        nohup python3 -m okbay serve >>/tmp/okbayd.log 2>&1 &
    elif command -v okbayd >/dev/null 2>&1; then
      OKBAY_WORKSPACE="$want" OKBAY_VIEWER_MODE=html nohup okbayd --port 8766 >>/tmp/okbayd.log 2>&1 &
    elif command -v okbay >/dev/null 2>&1; then
      OKBAY_WORKSPACE="$want" OKBAY_VIEWER_MODE=html nohup okbay serve >>/tmp/okbayd.log 2>&1 &
    fi
  fi

  for _ in $(seq 1 24); do
    sleep 0.25
    cur="$(okbay_status_workspace || true)"
    if [[ -n "$cur" ]]; then
      log "okbay up workspace=$cur"
      return 0
    fi
    if curl -fsS -m 1 "${OKBAY_URL}/health" >/dev/null 2>&1; then
      log "okbay health ok (status workspace pending)"
      return 0
    fi
  done
  log "okbay serve not confirmed; continuing"
  return 0
}

resolve_nautilus_path() {
  local cand
  for cand in \
    "${OKBAY_WORKSPACE:-}" \
    "/mnt/mac/Workspaces/${BIOCURE_NAME}" \
    "${HOME}/Workspaces/${BIOCURE_NAME}" \
    "${HOME}/Work/Workspaces/${BIOCURE_NAME}" \
    "${HOME}/Work/okbay"
  do
    [[ -n "$cand" && -d "$cand" ]] || continue
    if [[ -d "$cand/wiki" ]]; then
      printf '%s\n' "$cand/wiki"
      return 0
    fi
    if [[ -d "$cand/vault" ]]; then
      printf '%s\n' "$cand/vault"
      return 0
    fi
    printf '%s\n' "$cand"
    return 0
  done
  printf '%s\n' "${HOME}"
}

current_workspace_id() {
  if ! command -v hyprctl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' ""
    return 0
  fi
  hyprctl activeworkspace -j 2>/dev/null | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get("id") or "")
except Exception:
    print("")
' 2>/dev/null || printf '%s\n' ""
}

kill_stale_fullscreen_atlas() {
  # Kill leftover fullscreen Atlas on the *previous* (and any non-target) workspace
  # before we enter full-product mode. Leaves a clean slate for TL pane.
  command -v hyprctl >/dev/null 2>&1 || return 0
  command -v python3 >/dev/null 2>&1 || return 0
  local prev="$1"
  local target="$2"
  log "kill_stale_fullscreen_atlas prev=$prev target=$target"
  PREV_WS="$prev" TARGET_WS="$target" python3 - <<'PY' >>"$LOG" 2>&1 || true
import json, os, subprocess, time

def run(args):
    return subprocess.run(args, capture_output=True, text=True)

def dsp(lua):
    return run(["hyprctl", "dispatch", lua])

try:
    clients = json.loads(subprocess.check_output(["hyprctl", "clients", "-j"], text=True))
except Exception as e:
    print("clients err", e)
    raise SystemExit(0)

prev = str(os.environ.get("PREV_WS") or "")
target = str(os.environ.get("TARGET_WS") or "")

def is_atlas(c):
    cls = c.get("class")
    if isinstance(cls, list):
        classes = " ".join(str(x) for x in cls)
    else:
        classes = str(cls or "")
    blob = " ".join([
        classes,
        str(c.get("initialClass") or ""),
        str(c.get("title") or ""),
        str(c.get("initialTitle") or ""),
    ]).lower()
    return (
        "okbayatlas" in blob
        or "8766/atlas" in blob
        or ("atlas" in blob and ("chromium" in blob or "chrome" in blob))
        or (blob.startswith("chrome-") and ("atlas" in blob or "8766" in blob))
        or ("chrome-" in blob and ("atlas" in blob or "8766" in blob))
    )

killed = 0
for c in clients:
    if not is_atlas(c):
        continue
    ws = c.get("workspace") or {}
    ws_id = str(ws.get("id") or "")
    ws_name = str(ws.get("name") or "")
    on_target = (target and (ws_id == target or ws_name == target))
    fs = c.get("fullscreen") or 0
    try:
        fs_on = bool(int(fs))
    except Exception:
        fs_on = bool(fs)
    addr = c.get("address")
    if not addr:
        continue
    should = False
    if prev and (ws_id == prev or ws_name == prev) and (fs_on or c.get("floating")):
        should = True
    if not on_target and fs_on:
        should = True
    if not should:
        if on_target and fs_on:
            # Omarchy 0.56: mode=0 ENTERS fullscreen; toggle with mode="fullscreen"
            # NEVER float-unset — dumps product panes into dwindle before arrange.
            dsp(f'hl.dsp.focus({{ window = "address:{addr}" }})')
            dsp("hl.dsp.window.fullscreen({ mode = \"fullscreen\" })")
            # Omarchy: action=set TILES floating windows — only toggle when tiled
            if not c.get("floating"):
                dsp(f'hl.dsp.window.float({{ action = "toggle", window = "address:{addr}" }})')
            print("unset fs keep float on target Atlas", addr)
        continue
    print("close stale Atlas", addr, "ws", ws_id, ws_name, "fs", fs)
    dsp(f'hl.dsp.focus({{ window = "address:{addr}" }})')
    if fs_on:
        dsp("hl.dsp.window.fullscreen({ mode = \"fullscreen\" })")
    dsp(f'hl.dsp.window.close({{ window = "address:{addr}" }})')
    killed += 1
    time.sleep(0.1)
print("stale_atlas_killed", killed)
PY
}

pick_workspace() {
  local want="${OKBAY_FULL_PRODUCT_WS:-next-empty}"
  if [[ "$want" == special:* || "$want" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "$want"
    return 0
  fi
  if ! command -v hyprctl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "2"
    return 0
  fi
  hyprctl clients -j 2>/dev/null | python3 -c '
import json, sys
try:
    clients = json.load(sys.stdin)
except Exception:
    print(2); raise SystemExit
used = set()
for c in clients:
    try:
        used.add(int(c.get("workspace", {}).get("id") or 0))
    except Exception:
        pass
for n in range(2, 12):
    if n not in used:
        print(n); raise SystemExit
print(9)
' 2>/dev/null || printf '%s\n' "2"
}

switch_workspace() {
  local ws="$1"
  command -v hyprctl >/dev/null 2>&1 || return 0
  # Omarchy Hyprland 0.56: Lua dispatcher (classic `workspace N` → ')' expected)
  hyprctl dispatch 'hl.dsp.focus({ workspace = "'"$ws"'" })' >/dev/null 2>&1 || true
  log "switched to workspace $ws (hl.dsp.focus)"
}

launch_atlas_tiled() {
  local helper="" cand
  for cand in \
    "${SCRIPT_DIR}/okbay-open-atlas.sh" \
    "${HOME}/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-atlas.sh" \
    "${HOME}/.local/bin/okbay-open-atlas.sh"
  do
    if [[ -x "$cand" ]]; then
      helper="$cand"
      break
    fi
  done
  # Hard force: full-product never inherits a solo --start-fullscreen Atlas.
  export OKBAY_ATLAS_TILED=1
  # Drop any existing Atlas before helper runs (belt + suspenders with open-atlas).
  pkill -f 'chromium.*(8766/atlas|OkbayAtlas|--class=OkbayAtlas)' 2>/dev/null || true
  sleep 0.2
  if [[ -n "$helper" ]]; then
    OKBAY_ATLAS_TILED=1 "$helper" "$@" >/dev/null 2>&1 || true
  else
    log "okbay-open-atlas.sh missing"
  fi
  # Evidence: cmdline must NOT contain --start-fullscreen
  sleep 0.3
  if command -v pgrep >/dev/null 2>&1; then
    local cmd
    cmd="$(pgrep -af 'chromium.*(8766/atlas|OkbayAtlas)' 2>/dev/null | head -1 || true)"
    log "atlas cmdline: ${cmd:-none}"
    if [[ "$cmd" == *--start-fullscreen* ]]; then
      log "ERROR atlas still has --start-fullscreen; killing and relaunching tiled"
      pkill -f 'chromium.*(8766/atlas|OkbayAtlas|--class=OkbayAtlas)' 2>/dev/null || true
      sleep 0.2
      OKBAY_ATLAS_TILED=1 "$helper" "$@" >/dev/null 2>&1 || true
      sleep 0.3
      cmd="$(pgrep -af 'chromium.*(8766/atlas|OkbayAtlas)' 2>/dev/null | head -1 || true)"
      log "atlas cmdline retry: ${cmd:-none}"
    fi
  fi
  # Hypr: drop fullscreen even if windowrules re-applied (Lua hl.dsp.*)
  if command -v hyprctl >/dev/null 2>&1; then
    hyprctl clients -j 2>/dev/null | python3 -c '
import json,subprocess,sys
try:
    clients=json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
def dsp(lua):
    subprocess.run(["hyprctl","dispatch",lua],capture_output=True)
for c in clients:
    blob=" ".join(str(x) for x in [
        c.get("class"), c.get("initialClass"), c.get("title"), c.get("initialTitle")
    ]).lower()
    if (
        "okbayatlas" not in blob
        and "8766/atlas" not in blob
        and not ("chrome-" in blob and ("atlas" in blob or "8766" in blob))
        and not ("atlas" in blob and "chrome" in blob)
    ):
        continue
    addr=c.get("address") or ""
    if not addr:
        continue
    fs = c.get("fullscreen") or 0
    try:
        fs_on = bool(int(fs))
    except Exception:
        fs_on = bool(fs)
    dsp("hl.dsp.focus({ window = \"address:%s\" })" % addr)
    # Omarchy 0.56: mode=0 ENTERS fs; only toggle OFF when already fullscreen.
    # NEVER float-unset — arrange needs float set for absolute 2x2 place.
    if fs_on:
        dsp("hl.dsp.window.fullscreen({ mode = \"fullscreen\" })")
    if not c.get("floating"):
        dsp("hl.dsp.window.float({ action = \"toggle\", window = \"address:%s\" })" % addr)
' 2>/dev/null || true
  fi
}

launch_nautilus() {
  local path
  path="$(resolve_nautilus_path)"
  log "nautilus path=$path"
  if command -v uwsm-app >/dev/null 2>&1; then
    nohup uwsm-app -- nautilus --new-window "$path" >/tmp/okbay-nautilus.log 2>&1 &
  elif command -v omarchy-launch-nautilus >/dev/null 2>&1; then
    nohup omarchy-launch-nautilus "$path" >/tmp/okbay-nautilus.log 2>&1 &
  else
    nohup nautilus --new-window "$path" >/tmp/okbay-nautilus.log 2>&1 &
  fi
}

launch_herdr() {
  log "launch herdr"
  # Prefer foot --app-id=herdr BEFORE omarchy-launch-terminal-herdr.
  # The Omarchy helper runs `foot ... herdr` without --app-id, so Hyprland
  # reports class=foot title=omarchy: mac — arrange never classifies herdr.
  local has=0
  if command -v hyprctl >/dev/null 2>&1; then
    if hyprctl clients -j 2>/dev/null | python3 -c '
import json,sys
try:
    cs=json.load(sys.stdin)
except Exception:
    raise SystemExit(1)
for c in cs:
    blob=" ".join(str(x) for x in [c.get("class"),c.get("initialClass"),c.get("title"),c.get("initialTitle")]).lower()
    cls=str(c.get("class") or "").lower()
    title=str(c.get("title") or "").lower()
    initial=str(c.get("initialTitle") or "").lower()
    if cls=="herdr" or title=="herdr" or initial=="herdr" or "herdr" in blob:
        raise SystemExit(0)
raise SystemExit(1)
' 2>/dev/null; then
      has=1
    fi
  fi
  if [[ "$has" -eq 1 ]]; then
    log "herdr already mapped (app-id/title)"
    return 0
  fi
  if command -v foot >/dev/null 2>&1 && command -v herdr >/dev/null 2>&1; then
    if command -v uwsm-app >/dev/null 2>&1; then
      log "herdr via uwsm-app -- foot --app-id=herdr -T Herdr"
      nohup uwsm-app -- foot --app-id=herdr -T Herdr -e herdr >>/tmp/okbay-herdr.log 2>&1 &
    else
      log "herdr via foot --app-id=herdr -T Herdr"
      nohup foot --app-id=herdr -T Herdr -e herdr >>/tmp/okbay-herdr.log 2>&1 &
    fi
    sleep 0.55
    if command -v hyprctl >/dev/null 2>&1; then
      if hyprctl clients -j 2>/dev/null | grep -qiE '"class"[[:space:]]*:[[:space:]]*"herdr"|"title"[[:space:]]*:[[:space:]]*"Herdr"'; then
        log "herdr mapped with app-id/title"
        return 0
      fi
    fi
  fi
  # Soft API nudge (may spawn unclassified foot — only if foot path missing)
  if command -v curl >/dev/null 2>&1; then
    curl -fsS -m 2 -X POST "${OKSTRATR_URL}/api/herdr/launch" \
      -H 'Content-Type: application/json' \
      -d '{}' >/dev/null 2>&1 \
    || curl -fsS -m 2 -X POST "${OKSTRATR_URL}/api/desk/start" \
      -H 'Content-Type: application/json' \
      -d '{"kind":"auto","drive_herdr":true}' >/dev/null 2>&1 \
    || true
    sleep 0.35
  fi
  if command -v omarchy-launch-terminal-herdr >/dev/null 2>&1; then
    log "herdr fallback omarchy-launch-terminal-herdr"
    nohup omarchy-launch-terminal-herdr >>/tmp/okbay-herdr.log 2>&1 &
  elif command -v herdr >/dev/null 2>&1; then
    log "herdr direct fallback"
    nohup herdr >>/tmp/okbay-herdr.log 2>&1 &
  else
    log "herdr binary/launcher missing"
  fi
}

okstratr_client_mapped() {
  command -v hyprctl >/dev/null 2>&1 || return 1
  command -v python3 >/dev/null 2>&1 || return 1
  hyprctl clients -j 2>/dev/null | python3 -c '
import json,sys
try:
    cs=json.load(sys.stdin)
except Exception:
    raise SystemExit(1)
for c in cs:
    title=str(c.get("title") or "")
    initial=str(c.get("initialTitle") or "")
    cls=str(c.get("class") or "").lower()
    initial_cls=str(c.get("initialClass") or "").lower()
    t=(title+" "+initial).lower()
    if t.strip() == "okstratr" or "okstratr" in t or "benjsmith.okstratr" in t:
        raise SystemExit(0)
    if c.get("floating") and (cls in ("qs","quickshell") or "quickshell" in cls or initial_cls in ("qs","quickshell")):
        size=c.get("size") or [0,0]
        try:
            w,h=int(size[0] or 0),int(size[1] or 0)
        except Exception:
            w=h=0
        if w>=400 and h>=300:
            raise SystemExit(0)
raise SystemExit(1)
' 2>/dev/null
}

summon_okstratr_panel() {
  log "summon okstratr panel"
  if ! command -v omarchy-shell >/dev/null 2>&1; then
    log "omarchy-shell missing; cannot summon okstratr"
    return 0
  fi
  # Primary: panel surface (Quickshell FloatingWindow title Okstratr)
  local attempt
  for attempt in 1 2 3 4; do
    if okstratr_client_mapped; then
      log "okstratr already mapped"
      return 0
    fi
    log "okstratr summon attempt=$attempt"
    omarchy-shell -q shell summon benjsmith.okstratr '{"surface":"panel"}' >/dev/null 2>&1 \
      || omarchy-shell shell summon benjsmith.okstratr '{"surface":"panel"}' >/dev/null 2>&1 \
      || true
    sleep 0.55
    if okstratr_client_mapped; then
      log "okstratr mapped after panel summon"
      return 0
    fi
    omarchy-shell -q shell summon benjsmith.okstratr '{"surface":"desk"}' >/dev/null 2>&1 || true
    sleep 0.45
    if okstratr_client_mapped; then
      log "okstratr mapped after desk summon"
      return 0
    fi
  done
  log "okstratr still not mapped after retries"
}

arrange_2x2() {
  command -v hyprctl >/dev/null 2>&1 || return 0
  command -v python3 >/dev/null 2>&1 || return 0
  local ws="$1"
  local helper="${SCRIPT_DIR}/okbay-arrange-full-product.py"
  if [[ ! -f "$helper" ]]; then
    helper="${HOME}/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-arrange-full-product.py"
  fi
  if [[ ! -f "$helper" ]]; then
    helper="${HOME}/.local/bin/okbay-arrange-full-product.py"
  fi
  if [[ ! -f "$helper" ]]; then
    helper="${HOME}/.local/share/okbay/okbay-arrange-full-product.py"
  fi
  if [[ -f "$helper" ]]; then
    # Arrange writes ARRANGE_DONE + GEO to LOG itself (avoid >>LOG double lines)
    OKBAY_FULL_PRODUCT_LOG="$LOG" WS_TARGET="$ws" OKBAY_KILL_STALE_ATLAS=1 \
      OKBAY_ARRANGE_WAIT="${OKBAY_ARRANGE_WAIT:-22}" \
      python3 "$helper" 2>>"$LOG" || log "arrange exit=$?"
  else
    log "arrange helper missing: $helper"
  fi
}

PREV_WS="$(current_workspace_id)"
ensure_okbay_serve
ensure_okstratr_serve
WS="$(pick_workspace)"
log "prev workspace=$PREV_WS target workspace=$WS"
kill_stale_fullscreen_atlas "$PREV_WS" "$WS"
switch_workspace "$WS"
launch_atlas_tiled "$@"
sleep 1.2
launch_nautilus
sleep 0.35
launch_herdr
sleep 0.55
summon_okstratr_panel
sleep 1.0
switch_workspace "$WS"
arrange_2x2 "$WS"
log "full-product done ws=$WS"
exit 0
