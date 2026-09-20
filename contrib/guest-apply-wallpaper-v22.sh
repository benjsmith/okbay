#!/usr/bin/env bash
# Apply Switchbay wallpaper v22 on Omarchy guest.
# Prefer from Mac Mini:
#   ssh omarchy 'bash -s' < contrib/guest-apply-wallpaper-v22.sh
# Or after git pull of feat/skill-shell-rationalization on guest.
set -euo pipefail
REPO="${OKBAY_REPO:-$HOME/src/okbay}"
THEME_BG="$HOME/.config/omarchy/themes/switchbay/backgrounds"
SRC_BG="$REPO/themes/switchbay/backgrounds"
PRIMARY="${1:-1-okbay-night.png}"

cd "$REPO"
git fetch origin feat/skill-shell-rationalization
git checkout feat/skill-shell-rationalization
git pull --ff-only origin feat/skill-shell-rationalization

mkdir -p "$THEME_BG"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude archive/ "$SRC_BG/" "$THEME_BG/"
else
  cp -a "$SRC_BG"/*.png "$THEME_BG/"
  cp -a "$SRC_BG"/*.svg "$THEME_BG/" 2>/dev/null || true
fi

TARGET="$THEME_BG/$PRIMARY"
test -f "$TARGET"

if command -v omarchy-theme-bg-set >/dev/null 2>&1; then
  omarchy-theme-bg-set "$TARGET"
else
  omarchy theme set switchbay 2>/dev/null || omarchy-theme-set switchbay 2>/dev/null || true
  omarchy-theme-bg-set "$TARGET" 2>/dev/null || true
fi

STATE_BG="$HOME/.local/state/omarchy/current/background"
mkdir -p "$(dirname "$STATE_BG")"
ln -sfn "$TARGET" "$STATE_BG"

omarchy-shell -q background set "$TARGET" 2>/dev/null || true
hyprctl hyprpaper reload 2>/dev/null || true

echo "guest-apply-wallpaper-v22: $(git rev-parse --short HEAD) -> $TARGET"
ls -la "$TARGET" "$STATE_BG"
