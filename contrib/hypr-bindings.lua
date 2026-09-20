-- OKBay Atlas / Reviews — optional Omarchy Hyprland binds (Super+K discoverable).
-- Install: merge into ~/.config/hypr/bindings.lua (loaded after Omarchy defaults).
-- setup.sh copies contrib/okbay-open-atlas.sh next to the plugin and documents the bind.
-- In-page Atlas nav (/, arrows, Ctrl+Arrow, Alt+Arrow, WASD, l, t, …) lives in
-- atlas-chrome.js — Super+Arrow is owned by Hyprland tiling and must not be rebound.
--
-- Note: Omarchy default Super+Shift+O is Obsidian (preinstalled); Okstratr owns
-- that override and unbinds it first. OKBay Atlas uses Super+Shift+K.

-- Open / focus Atlas (single Chromium focus-or-launch; no plugin summon).
-- Requires OMARCHY_PATH; the helper exports it when missing (SSH / non-Hypr envs).
-- Summon raced Chromium and opened two windows — keep Super+Shift+K Chromium-only.
hl.unbind("SUPER + SHIFT + K")
o.bind("SUPER + SHIFT + K", "OKBay Atlas", {
  launch = "~/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-atlas.sh",
})

-- Optional: Reviews panel (also available as Super+Ctrl+1 when Okbay is bar panel #1).
-- o.bind("SUPER + SHIFT + ALT + K", "OKBay Reviews", {
--   launch = "omarchy-shell shell summon benjsmith.okbay '{\"surface\":\"panel\"}'",
-- })

--[[
  Frameless / option-3 windowrules (Hyprland).

  Guest-ready snippet lives in contrib/okbay-atlas.conf. Prefer:
    contrib/setup.sh
    # or
    contrib/install-okbay-atlas-rules.sh
    hyprctl reload

  Chromium --app= + --class=OkbayAtlas (see okbay-open-atlas.sh). Rules:

    windowrulev2 = float, class:^(OkbayAtlas)$
    windowrulev2 = fullscreen, class:^(OkbayAtlas)$

  Launcher already focus-or-launches one window — do not also summon the
  Quickshell surface on Super+Shift+K (double-window race).
]]
