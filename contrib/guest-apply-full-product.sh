#!/usr/bin/env bash
# Apply okbay full-product 2x2 launcher onto a live Omarchy guest.
# Prefer from Mac Mini host:
#   ssh omarchy 'bash -s' < contrib/guest-apply-full-product.sh
#   # or: ssh -p 2222 benj@127.0.0.1 'bash -s' < contrib/guest-apply-full-product.sh
# On guest after git pull of feat/skill-shell-rationalization:
#   bash ~/src/okbay/contrib/guest-apply-full-product.sh
set -euo pipefail
REPO="${OKBAY_SRC:-$HOME/src/okbay}"
BRANCH="${OKBAY_BRANCH:-feat/skill-shell-rationalization}"
LIVE_BIN="${HOME}/.local/bin/okbay-open-full-product.sh"
PLUGIN_CONTRIB="${HOME}/.config/omarchy/plugins/benjsmith.okbay/contrib"

cd "$REPO"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

mkdir -p "${HOME}/.local/bin" "$PLUGIN_CONTRIB"
for f in okbay-open-full-product.sh okbay-open-atlas.sh okbay-arrange-full-product.py; do
  install -m 0755 "$REPO/contrib/$f" "${HOME}/.local/bin/$f"
  install -m 0755 "$REPO/contrib/$f" "$PLUGIN_CONTRIB/$f"
done
install -m 0644 "$REPO/contrib/hypr-bindings.lua" "$PLUGIN_CONTRIB/hypr-bindings.lua"

BINDINGS_LUA="${HOME}/.config/hypr/bindings.lua"
mkdir -p "${HOME}/.config/hypr"
if [[ ! -f "$BINDINGS_LUA" ]]; then
  cp "$REPO/contrib/hypr-bindings.lua" "$BINDINGS_LUA"
elif ! grep -q 'okbay-open-full-product.sh' "$BINDINGS_LUA" 2>/dev/null; then
  cat >> "$BINDINGS_LUA" <<'BINDEOF'

-- OKBay full product 2x2 (guest-apply-full-product.sh)
hl.unbind("SUPER + SHIFT + K")
o.bind("SUPER + SHIFT + K", "OKBay full product (2x2 workspace)", {
  launch = "~/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-full-product.sh",
})
hl.unbind("SUPER + CTRL + K")
o.bind("SUPER + CTRL + K", "OKBay full product (Mac alt)", {
  launch = "~/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-full-product.sh",
})
BINDEOF
fi

if ! grep -q 'SUPER + SHIFT + M' "$BINDINGS_LUA" 2>/dev/null; then
  cat >> "$BINDINGS_LUA" <<'NOTEOF'

-- Personal (Mac Mini): keep Super+Shift+S as screenshot; Maps on Super+Shift+M.
-- Uncomment if Omarchy default still binds Maps to Super+Shift+S:
-- hl.unbind("SUPER + SHIFT + S")
-- o.bind("SUPER + SHIFT + M", "Maps", { launch = "omarchy-launch-webapp https://maps.google.com" })
NOTEOF
fi

hyprctl reload 2>/dev/null || true
echo "guest-apply-full-product: $(git rev-parse --short HEAD) -> $LIVE_BIN"
echo "Verify: Super+Shift+K (or: $LIVE_BIN) -> new workspace 2x2 Atlas|Nautilus / Herdr|okstratr"
echo "Log: /tmp/okbay-full-product.log"
