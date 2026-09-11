-- OKBay Atlas / Reviews — optional Omarchy Hyprland binds (Super+K discoverable).
-- Install: merge into ~/.config/hypr/bindings.lua (loaded after Omarchy defaults).
-- In-page Atlas nav (/, arrows, Ctrl+Arrow, Alt+Arrow, WASD, l, t, …) lives in
-- atlas-chrome.js — Super+Arrow is owned by Hyprland tiling and must not be rebound.

-- Open / focus Atlas Chromium --app= window (avoids Super+K keybindings viewer).
o.bind("SUPER + SHIFT + K", "OKBay Atlas", {
  launch = "omarchy-shell shell summon benjsmith.okbay '{\"surface\":\"atlas\"}'",
})

-- Optional: Reviews panel (also available as Super+Ctrl+1 when Okbay is bar panel #1).
-- o.bind("SUPER + SHIFT + ALT + K", "OKBay Reviews", {
--   launch = "omarchy-shell shell summon benjsmith.okbay '{\"surface\":\"panel\"}'",
-- })
