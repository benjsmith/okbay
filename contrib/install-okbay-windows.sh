#!/usr/bin/env bash
# Install contrib/okbay-windows.lua into a Lua Hyprland config (Hyprland 0.56+,
# as used by Omarchy) and load it from hyprland.lua. It brings grok's device
# sign-in browser window to the front, above the Super+Shift+K 2x2 layout.
# Safe to re-run. Does nothing on hyprlang (.conf) setups.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HYPR="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
MAIN="$HYPR/hyprland.lua"
REQUIRE_LINE='require("hypr.okbay-windows")'

if [ ! -f "$MAIN" ]; then
  echo "==> no $MAIN; skipping okbay-windows.lua (hyprlang setups use okbay-atlas.conf)"
  exit 0
fi
install -m 0644 "$REPO_ROOT/contrib/okbay-windows.lua" "$HYPR/okbay-windows.lua"
echo "==> installed $HYPR/okbay-windows.lua"
if grep -q 'hypr.okbay-windows' "$MAIN"; then
  echo "==> $MAIN already loads okbay-windows"
else
  printf '\n-- okbay: bring the grok sign-in window to the front\n%s\n' "$REQUIRE_LINE" >> "$MAIN"
  echo "==> added $REQUIRE_LINE to $MAIN"
fi
if [ "${OKBAY_NO_RELOAD:-0}" != "1" ] && command -v hyprctl >/dev/null 2>&1; then
  hyprctl reload >/dev/null 2>&1 && echo "==> hyprctl reload ok" || echo "==> hyprctl reload failed; it loads on next login"
fi
