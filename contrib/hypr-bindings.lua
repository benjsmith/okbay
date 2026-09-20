-- OKBay full-product / Atlas — optional Omarchy Hyprland binds.
-- Install: merge into ~/.config/hypr/bindings.lua (loaded after Omarchy defaults).
-- setup.sh installs contrib/okbay-open-full-product.sh (+ atlas helper) and documents binds.
-- In-page Atlas nav (/, arrows, Ctrl+Arrow, Alt+Arrow, WASD, l, t, …) lives in
-- atlas-chrome.js — Super+Arrow is owned by Hyprland tiling and must not be rebound.
--
-- Note: Omarchy default Super+Shift+O is Obsidian (preinstalled); Okstratr owns
-- that override (okstratr-only panel). OKBay full-product uses Super+Shift+K.
-- On Mac host key steal of Super+Shift+K, use Super+Ctrl+K (same launcher).
--
-- Personal chord note (do NOT edit /usr/share/omarchy defaults): live Mac Mini
-- guest unbinds Omarchy Maps from Super+Shift+S so Super+Shift+S stays screenshot.
-- Maps → Super+Alt+S (NOT Super+Shift+M — that is Omarchy Music). Mirror in
-- ~/.config/hypr/bindings.lua only — never patch /usr/share/omarchy/default/….

-- Full product: new/empty Hyprland workspace + 2x2 panes
-- (Atlas TL, Nautilus TR, Herdr BL, okstratr BR). Not float-over-current.
hl.unbind("SUPER + SHIFT + K")
o.bind("SUPER + SHIFT + K", "OKBay full product (2x2 workspace)", {
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

  Chromium --app= + --class=OkbayAtlas (see okbay-open-atlas.sh). Solo Atlas
  may use float/fullscreen rules; full-product Super+Shift+K launches with
  OKBAY_ATLAS_TILED=1 and arranges a 2x2 grid on a fresh workspace — the
  launcher unsets fullscreen so Atlas does not cover the prior desktop.

  Optional personal binds (user ~/.config/hypr/bindings.lua only):
    hl.unbind("SUPER + SHIFT + S")  -- keep screenshot; Maps unbound from Shift+S
    o.bind("SUPER + ALT + S", "Maps", { … })  -- NOT Super+Shift+M (Music)
]]
