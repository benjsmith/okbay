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
#   1) Switch to a fresh / dedicated Hyprland workspace
#   2) Populate a 2x2 panel split:
#        Top-left:     okbay / Atlas   (class OkbayAtlas)
#        Top-right:    Nautilus        (org.gnome.Nautilus)
#        Bottom-left:  Herdr
#        Bottom-right: okstratr panel
#
# Env knobs:
#   OKBAY_FULL_PRODUCT_WS   workspace target: "next-empty" (default), a number,
#                           or "special:okbay"
#   OKBAY_WORKSPACE         wiki/vault root for Nautilus (else well-known paths)
#   OKSTRATR_URL            default http://127.0.0.1:8767
#   OKBAY_ATLAS_URL         Atlas URL for the TL pane
set -u
export OMARCHY_PATH="${OMARCHY_PATH:-/usr/share/omarchy}"
export PATH="${HOME}/.local/bin:/usr/bin:${PATH}"
export OKBAY_ATLAS_TILED="${OKBAY_ATLAS_TILED:-1}"

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

OKSTRATR_URL="${OKSTRATR_URL:-http://127.0.0.1:8767}"
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

resolve_nautilus_path() {
  local cand
  for cand in \
    "${OKBAY_WORKSPACE:-}" \
    "${HOME}/Work/Workspaces/biocure-confirm-v1-query-5b9711895" \
    "${HOME}/Workspaces/biocure-confirm-v1-query-5b9711895" \
    "/mnt/mac/Workspaces/biocure-confirm-v1-query-5b9711895" \
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
  hyprctl dispatch workspace "$ws" >/dev/null 2>&1 || true
  log "switched to workspace $ws"
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
  export OKBAY_ATLAS_TILED=1
  if [[ -n "$helper" ]]; then
    "$helper" "$@" >/dev/null 2>&1 || true
  else
    log "okbay-open-atlas.sh missing"
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
  if command -v curl >/dev/null 2>&1; then
    curl -fsS -m 2 -X POST "${OKSTRATR_URL}/api/herdr/launch" \
      -H 'Content-Type: application/json' \
      -d '{}' >/dev/null 2>&1 \
    || curl -fsS -m 2 -X POST "${OKSTRATR_URL}/api/desk/start" \
      -H 'Content-Type: application/json' \
      -d '{"kind":"auto","drive_herdr":true}' >/dev/null 2>&1 \
    || true
  fi
  sleep 0.4
  if command -v hyprctl >/dev/null 2>&1; then
    if ! hyprctl clients -j 2>/dev/null | grep -qi herdr; then
      if command -v uwsm-app >/dev/null 2>&1; then
        nohup uwsm-app -- herdr >/tmp/okbay-herdr.log 2>&1 &
      elif command -v herdr >/dev/null 2>&1; then
        nohup herdr >/tmp/okbay-herdr.log 2>&1 &
      elif command -v omarchy-launch-terminal-herdr >/dev/null 2>&1; then
        nohup omarchy-launch-terminal-herdr >/tmp/okbay-herdr.log 2>&1 &
      fi
    fi
  fi
}

summon_okstratr_panel() {
  if command -v omarchy-shell >/dev/null 2>&1; then
    omarchy-shell -q shell summon benjsmith.okstratr '{"surface":"panel"}' >/dev/null 2>&1 || true
  fi
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
    helper="${HOME}/.local/share/okbay/okbay-arrange-full-product.py"
  fi
  if [[ -f "$helper" ]]; then
    WS_TARGET="$ws" python3 "$helper" >>"$LOG" 2>&1 || true
  else
    log "arrange helper missing: $helper"
  fi
}

ensure_okstratr_serve
WS="$(pick_workspace)"
log "target workspace=$WS"
switch_workspace "$WS"
launch_atlas_tiled "$@"
sleep 0.35
launch_nautilus
sleep 0.25
launch_herdr
sleep 0.25
summon_okstratr_panel
sleep 0.45
switch_workspace "$WS"
arrange_2x2 "$WS"
log "full-product done ws=$WS"
exit 0
