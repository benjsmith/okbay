#!/usr/bin/env bash
# Install OkbayAtlas Hyprland windowrules and reload Hypr.
# Safe to re-run; does not touch keybinds.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO_ROOT/contrib/okbay-atlas.conf"
HYPR="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
DEST="$HYPR/okbay-atlas.conf"
mkdir -p "$HYPR"
install -m 0644 "$SRC" "$DEST"
echo "==> installed $DEST"

# Prefer sourcing from windows.conf (Omarchy) then hyprland.conf.
SOURCE_LINE='source = ~/.config/hypr/okbay-atlas.conf'
for conf in "$HYPR/windows.conf" "$HYPR/hyprland.conf"; do
  if [ -f "$conf" ]; then
    if grep -q 'okbay-atlas.conf' "$conf" 2>/dev/null; then
      echo "==> $conf already sources okbay-atlas.conf"
    else
      printf '\n# OKBay Atlas windowrules (setup)\n%s\n' "$SOURCE_LINE" >> "$conf"
      echo "==> appended source to $conf"
    fi
    break
  fi
done

if [ ! -f "$HYPR/windows.conf" ] && [ ! -f "$HYPR/hyprland.conf" ]; then
  # Minimal stub so guests without a conf yet can still load rules after linking.
  printf '%s\n' "$SOURCE_LINE" > "$HYPR/windows.conf"
  echo "==> created $HYPR/windows.conf with source line"
fi

if command -v hyprctl >/dev/null 2>&1; then
  if hyprctl reload >/dev/null 2>&1; then
    echo "==> hyprctl reload ok"
  else
    echo "==> hyprctl reload failed (not in a Hypr session?); rules install on next login"
  fi
else
  echo "==> hyprctl not on PATH; run: hyprctl reload"
fi
