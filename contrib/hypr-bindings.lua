-- OKBay Atlas / Reviews — optional Omarchy Hyprland binds (Super+K discoverable).
-- Install: merge into ~/.config/hypr/bindings.lua (loaded after Omarchy defaults).
-- setup.sh copies contrib/okbay-open-atlas.sh next to the plugin and documents the bind.
-- In-page Atlas nav (/, arrows, Ctrl+Arrow, Alt+Arrow, WASD, l, t, …) lives in
-- atlas-chrome.js — Super+Arrow is owned by Hyprland tiling and must not be rebound.
--
-- Note: Omarchy default Super+Shift+O is Obsidian (preinstalled). Okstratr may
-- override that chord; OKBay Atlas uses Super+Shift+K and does not steal Obsidian.

-- Open / focus Atlas (omarchy-shell summon, Chromium --app= fallback).
-- Requires OMARCHY_PATH; the helper exports it when missing (SSH / non-Hypr envs).
o.bind("SUPER + SHIFT + K", "OKBay Atlas", {
  launch = "~/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-atlas.sh",
})

-- Optional: Reviews panel (also available as Super+Ctrl+1 when Okbay is bar panel #1).
-- o.bind("SUPER + SHIFT + ALT + K", "OKBay Reviews", {
--   launch = "omarchy-shell shell summon benjsmith.okbay '{\"surface\":\"panel\"}'",
-- })
