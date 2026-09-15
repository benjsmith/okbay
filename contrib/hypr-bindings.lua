-- OKBay Atlas / Reviews — optional Omarchy Hyprland binds (Super+K discoverable).
-- Install: merge into ~/.config/hypr/bindings.lua (loaded after Omarchy defaults).
-- setup.sh copies contrib/okbay-open-atlas.sh next to the plugin and documents the bind.
-- In-page Atlas nav (/, arrows, Ctrl+Arrow, Alt+Arrow, WASD, l, t, …) lives in
-- atlas-chrome.js — Super+Arrow is owned by Hyprland tiling and must not be rebound.
--
-- Note: Omarchy default Super+Shift+O is Obsidian (preinstalled). Okstratr may
-- override that chord; OKBay Atlas uses Super+Shift+K and does not steal Obsidian.

-- Open / focus Atlas (single Chromium focus-or-launch; no plugin summon).
-- Requires OMARCHY_PATH; the helper exports it when missing (SSH / non-Hypr envs).
-- Summon raced Chromium and opened two windows — keep Super+Shift+K Chromium-only.
o.bind("SUPER + SHIFT + K", "OKBay Atlas", {
  launch = "~/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-atlas.sh",
})

-- Optional: Reviews panel (also available as Super+Ctrl+1 when Okbay is bar panel #1).
-- o.bind("SUPER + SHIFT + ALT + K", "OKBay Reviews", {
--   launch = "omarchy-shell shell summon benjsmith.okbay '{\"surface\":\"panel\"}'",
-- })

--[[
  Frameless / option-3 windowrules (Hyprland).

  Chromium --app= + --class=OkbayAtlas (see okbay-open-atlas.sh). Merge the
  following into ~/.config/hypr/windows.conf (or hyprland.conf windowrulev2
  section) when Omarchy exposes them. Prefer special workspace if you want
  Atlas off the tiling grid; fullscreen alone is enough for kiosk feel.

  # Single-instance feel: float or fullscreen on the OkbayAtlas class
  windowrulev2 = float, class:^(OkbayAtlas)$
  windowrulev2 = fullscreen, class:^(OkbayAtlas)$
  # Optional: pin to a dedicated special workspace (toggle with Super+S-style bind)
  # windowrulev2 = workspace special:okbay, class:^(OkbayAtlas)$
  # Optional: no blur/shadow chrome noise
  # windowrulev2 = noblur, class:^(OkbayAtlas)$
  # windowrulev2 = noshadow, class:^(OkbayAtlas)$

  Launcher already focus-or-launches one window — do not also summon the
  Quickshell surface on Super+Shift+K (double-window race).
]]
