#!/usr/bin/env bash
# Always install tip contrib scripts into ~/.local/bin (md5 must match).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
install -m 0755 "$ROOT/contrib/okbay-arrange-full-product.py" "$HOME/.local/bin/okbay-arrange-full-product.py"
install -m 0755 "$ROOT/contrib/okbay-open-full-product.sh" "$HOME/.local/bin/okbay-open-full-product.sh"
install -m 0755 "$ROOT/contrib/okbay-open-atlas.sh" "$HOME/.local/bin/okbay-open-atlas.sh"
if [[ -f "$ROOT/contrib/okbay-atlas.conf" ]]; then
  mkdir -p "$HOME/.config/hypr"
  cp -f "$ROOT/contrib/okbay-atlas.conf" "$HOME/.config/hypr/okbay-atlas.conf"
fi
echo "APPLIED $(cd "$ROOT" && git rev-parse --short HEAD 2>/dev/null || echo unknown)"
md5sum "$HOME/.local/bin/okbay-arrange-full-product.py" "$ROOT/contrib/okbay-arrange-full-product.py"
