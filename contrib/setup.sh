#!/usr/bin/env bash
# Visible installer. omarchy plugin add never runs this.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${OKBAY_PREFIX:-$HOME/.local}"
BIN="$PREFIX/bin"
WORKSPACE="${OKBAY_WORKSPACE:-$HOME/Work/okbay}"
mkdir -p "$BIN" "$HOME/.local/state/okbay" "$HOME/.config/okbay"
echo "==> building rust okbayd (warm daemon)"
if command -v cargo >/dev/null 2>&1; then
  export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$HOME/.cache/okbay/target}"
  mkdir -p "$CARGO_TARGET_DIR"
  (cd "$REPO_ROOT" && cargo build --release -p okbayd) || echo "(cargo build failed; python server remains the fallback)"
  if [ -x "$CARGO_TARGET_DIR/release/okbayd" ]; then
    install -m 0755 "$CARGO_TARGET_DIR/release/okbayd" "$BIN/okbayd-rs"
  elif [ -x "$REPO_ROOT/target/release/okbayd" ]; then
    install -m 0755 "$REPO_ROOT/target/release/okbayd" "$BIN/okbayd-rs"
  fi
fi
cat > "$BIN/okbay" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$REPO_ROOT/src:\${PYTHONPATH:-}"
exec python3 -m okbay "\$@"
EOF
chmod +x "$BIN/okbay"
cat > "$BIN/okbayd" <<EOF
#!/usr/bin/env bash
if [ -x "$BIN/okbayd-rs" ]; then exec "$BIN/okbayd-rs" "\$@"; fi
export PYTHONPATH="$REPO_ROOT/src:\${PYTHONPATH:-}"
exec python3 -m okbay serve "\$@"
EOF
chmod +x "$BIN/okbayd"
OKBAY_WORKSPACE="$WORKSPACE" "$BIN/okbay" setup --workspace "$WORKSPACE" || true
for dest in "$HOME/.agents/skills" "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.pi/agent/skills" "$HOME/.gemini/config/skills"; do
  mkdir -p "$dest"
  for skill in okbay-ask okbay-curate okbay-desk; do ln -sfn "$REPO_ROOT/skills/$skill" "$dest/$skill"; done
done
mkdir -p "$HOME/.config/systemd/user" "$HOME/.config/omarchy/themes" "$HOME/.config/omarchy/plugins/benjsmith.okbay" "$HOME/.config/omarchy/extensions"
cp "$REPO_ROOT/contrib/okbayd.service" "$HOME/.config/systemd/user/okbayd.service" 2>/dev/null || true
if [ -d "$REPO_ROOT/themes/switchbay" ]; then cp -a "$REPO_ROOT/themes/switchbay/." "$HOME/.config/omarchy/themes/switchbay/"; fi
for f in manifest.json BarWidget.qml Overlay.qml Panel.qml Service.qml Model.js LICENSE README.md; do
  [ -f "$REPO_ROOT/$f" ] && cp "$REPO_ROOT/$f" "$HOME/.config/omarchy/plugins/benjsmith.okbay/$f"
done
[ -f "$REPO_ROOT/contrib/okbay-menu.jsonc" ] && cp "$REPO_ROOT/contrib/okbay-menu.jsonc" "$HOME/.config/omarchy/extensions/okbay-menu.jsonc"
# Atlas opener + Hypr bind snippet (Super+Shift+K). Omarchy default Super+Shift+O is Obsidian.
mkdir -p "$HOME/.config/omarchy/plugins/benjsmith.okbay/contrib"
if [ -f "$REPO_ROOT/contrib/okbay-open-atlas.sh" ]; then
  install -m 0755 "$REPO_ROOT/contrib/okbay-open-atlas.sh"     "$HOME/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-atlas.sh"
  # Also keep a copy next to a src checkout if present
  if [ -d "$HOME/src/okbay/contrib" ]; then
    install -m 0755 "$REPO_ROOT/contrib/okbay-open-atlas.sh" "$HOME/src/okbay/contrib/okbay-open-atlas.sh"
  fi
fi
BINDINGS_LUA="$HOME/.config/hypr/bindings.lua"
if [ -f "$REPO_ROOT/contrib/hypr-bindings.lua" ]; then
  mkdir -p "$HOME/.config/hypr"
  if [ ! -f "$BINDINGS_LUA" ]; then
    cp "$REPO_ROOT/contrib/hypr-bindings.lua" "$BINDINGS_LUA"
    echo "==> installed $BINDINGS_LUA (Super+Shift+K → OKBay Atlas)"
  elif ! grep -q 'okbay-open-atlas.sh' "$BINDINGS_LUA" 2>/dev/null; then
    cat >> "$BINDINGS_LUA" <<'BINDEOF'

-- OKBay Atlas (setup.sh); replace the chord rather than accumulating duplicate binds.
hl.unbind("SUPER + SHIFT + K")
o.bind("SUPER + SHIFT + K", "OKBay Atlas", {
  launch = "~/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-atlas.sh",
})
BINDEOF
    echo "==> merged Super+Shift+K Atlas bind into $BINDINGS_LUA"
  else
    echo "==> $BINDINGS_LUA already references okbay-open-atlas.sh"
  fi
fi
# OkbayAtlas Hyprland windowrules (float/fullscreen); does not touch keybinds.
if [ -f "$REPO_ROOT/contrib/okbay-atlas.conf" ]; then
  if [ -x "$REPO_ROOT/contrib/install-okbay-atlas-rules.sh" ]; then
    "$REPO_ROOT/contrib/install-okbay-atlas-rules.sh" || true
  else
    mkdir -p "$HOME/.config/hypr"
    install -m 0644 "$REPO_ROOT/contrib/okbay-atlas.conf" "$HOME/.config/hypr/okbay-atlas.conf"
    echo "==> installed ~/.config/hypr/okbay-atlas.conf — run: hyprctl reload"
  fi
fi
# Also keep contrib scripts next to the plugin copy.
if [ -f "$REPO_ROOT/contrib/okbay-atlas.conf" ]; then
  install -m 0644 "$REPO_ROOT/contrib/okbay-atlas.conf"     "$HOME/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-atlas.conf"
fi
if [ -f "$REPO_ROOT/contrib/install-okbay-atlas-rules.sh" ]; then
  install -m 0755 "$REPO_ROOT/contrib/install-okbay-atlas-rules.sh"     "$HOME/.config/omarchy/plugins/benjsmith.okbay/contrib/install-okbay-atlas-rules.sh"
fi
systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable --now okbayd.service 2>/dev/null || echo "(systemd user unit not enabled)"
echo "Okbay setup complete. Atlas: http://127.0.0.1:8766/atlas"
echo "Hypr: Super+Shift+K → OKBay Atlas (unbinds before bind; helper sets OMARCHY_PATH). Super+Shift+O belongs to Okstratr when installed."
echo "Hypr windowrules: ~/.config/hypr/okbay-atlas.conf — after install: hyprctl reload"
