-- OKBay window handling for Omarchy's Lua Hyprland config (Hyprland 0.56+).
--
-- grok's device sign-in opens "Device Sign-in | ... Accounts" in the browser.
-- Omarchy tiles browsers, and the okbay 2x2 layout floats its four windows,
-- so a new sign-in window ended up underneath them. Chromium only sets that
-- title after the page loads, which is too late for a static window rule, so
-- this watches title changes instead.
--
-- When a window's title becomes the sign-in page:
--   * if the window opened in the last 30 seconds (the browser was started
--     just for the sign-in), float it, size it to 960x760 and centre it;
--   * in all cases focus it and raise it above other floating windows.
-- Each window is handled once, so later title changes leave it alone.
--
-- Install: setup.sh copies this to ~/.config/hypr/okbay-windows.lua and adds
-- require("hypr.okbay-windows") to ~/.config/hypr/hyprland.lua.

local M = {}

-- Any browser: Chromium, Chrome, Brave, Firefox all put the page title first.
M.title_pattern = "^Device Sign%-in"
M.fresh_seconds = 30
M.size = { 960, 760 }

local opened_at = {}
local handled = {}

function M.is_signin(w)
  if not w then return false end
  return (w.title or ""):find(M.title_pattern) ~= nil
end

-- Returns the dispatcher list for a sign-in window (exposed for tests).
function M.actions(w, now)
  local sel = "address:" .. w.address
  local list = {}
  local fresh = opened_at[w.address] and (now - opened_at[w.address]) <= M.fresh_seconds
  -- "toggle" rather than action = "set": on Omarchy 0.56 "set" can tile an
  -- already floating window.
  if fresh and not w.floating then
    list[#list + 1] = hl.dsp.window.float({ action = "toggle", window = sel })
    list[#list + 1] = hl.dsp.window.resize({ x = M.size[1], y = M.size[2], relative = false, window = sel })
    list[#list + 1] = hl.dsp.window.center({ window = sel })
  end
  list[#list + 1] = hl.dsp.focus({ window = sel })
  list[#list + 1] = hl.dsp.window.bring_to_top({ window = sel })
  return list
end

function M.on_open(w)
  if w and w.address then opened_at[w.address] = os.time() end
  M.on_title(w)
end

function M.on_title(w)
  if not M.is_signin(w) or handled[w.address] then return end
  handled[w.address] = true
  for _, d in ipairs(M.actions(w, os.time())) do
    pcall(hl.dispatch, d)
  end
end

function M.on_close(w)
  if w and w.address then
    opened_at[w.address] = nil
    handled[w.address] = nil
  end
end

if okbay_windows_subs then
  for _, s in ipairs(okbay_windows_subs) do pcall(function() s:remove() end) end
end
okbay_windows_subs = {
  hl.on("window.open", M.on_open),
  hl.on("window.title", M.on_title),
  hl.on("window.destroy", M.on_close),
}

return M
