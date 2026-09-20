-- OKBay full-product / Atlas — optional Omarchy Hyprland binds.
-- Install: merge into ~/.config/hypr/bindings.lua (loaded after Omarchy defaults).
-- setup.sh installs contrib/okbay-open-full-product.sh (+ atlas helper) and documents binds.
-- In-page Atlas nav (/, arrows, Ctrl+Arrow, Alt+Arrow, WASD, l, t, …) lives in
-- atlas-chrome.js — Super+Arrow is owned by Hyprland tiling and must not be rebound.
--
-- Note: Omarchy default Super+Shift+O is Obsidian (preinstalled); Okstratr owns
-- that override (okstratr-only panel). OKBay full-product uses Super+Shift+K.
-- On Mac host key steal of Super+Shift+K, use Super+Ctrl+K (same launcher).

-- Full product: okstratr summon + best-effort Herdr desk + Atlas opener.
hl.unbind("SUPER + SHIFT + K")
o.bind("SUPER + SHIFT + K", "OKBay full product", {
  launch = "~/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-full-product.sh",
})

-- Mac-host alt when Super+Shift+K is stolen by the host (replaces Omarchy Herdr cheat sheet).
hl.unbind("SUPER + CTRL + K")
o.bind("SUPER + CTRL + K", "OKBay full product (Mac alt)", {
  launch = "~/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-full-product.sh",
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

  Full-product launcher summons okstratr then focus-or-launches one Atlas
  Chromium — do not also summon the Quickshell atlas surface on K (double-window).
]]
