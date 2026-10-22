-- Runs contrib/okbay-windows.lua against a stub `hl` and prints what it did.
local path = arg[1]
local calls, handlers = {}, {}
local function dsp(name)
  return function(args) return { name = name, args = args } end
end
hl = {
  dsp = {
    focus = dsp("focus"),
    window = {
      float = dsp("float"), resize = dsp("resize"), center = dsp("center"),
      bring_to_top = dsp("bring_to_top"),
    },
  },
  dispatch = function(d) calls[#calls + 1] = d end,
  on = function(ev, fn)
    handlers[ev] = fn
    return { remove = function() handlers[ev] = nil end }
  end,
}
local now = 1000
os.time = function() return now end
local M = dofile(path)

local function run(label, steps)
  calls = {}
  for _, s in ipairs(steps) do
    if s.advance then now = now + s.advance end
    if s.ev then handlers[s.ev](s.w) end
  end
  local out = {}
  for _, c in ipairs(calls) do
    local a = c.args or {}
    out[#out + 1] = c.name .. "(" .. tostring(a.window) .. (a.action and ("," .. a.action) or "")
      .. (a.x and ("," .. a.x .. "x" .. a.y) or "") .. ")"
  end
  print(label .. ": " .. table.concat(out, " "))
end

local fresh = { address = "0x1", class = "chromium", title = "Untitled - Chromium", floating = false }
run("fresh-open", { { ev = "window.open", w = fresh } })
fresh.title = "Device Sign-in | SpaceXAI Accounts - Chromium"
run("fresh-title", { { advance = 2, ev = "window.title", w = fresh } })
fresh.title = "Authorize — Grok | SpaceXAI Accounts - Chromium"
run("fresh-again", { { ev = "window.title", w = fresh } })

local old = { address = "0x2", class = "chromium", title = "News - Chromium", floating = false }
run("old-open", { { ev = "window.open", w = old } })
old.title = "Device Sign-in | SpaceXAI Accounts - Chromium"
run("old-title", { { advance = 120, ev = "window.title", w = old } })

local other = { address = "0x3", class = "chromium", title = "Sign in - Google Accounts", floating = false }
run("other", { { ev = "window.open", w = other }, { ev = "window.title", w = other } })

local floated = { address = "0x4", class = "firefox", title = "x", floating = true }
run("floated-open", { { ev = "window.open", w = floated } })
floated.title = "Device Sign-in | SpaceXAI Accounts — Mozilla Firefox"
run("floated-title", { { ev = "window.title", w = floated } })

run("closed", { { ev = "window.destroy", w = fresh } })
fresh.title = "Device Sign-in | SpaceXAI Accounts - Chromium"
run("reused", { { ev = "window.open", w = fresh }, { ev = "window.title", w = fresh } })

-- Loading the file twice (hyprctl reload) keeps one set of handlers.
local count = 0
for _ in pairs(handlers) do count = count + 1 end
dofile(path)
local count2 = 0
for _ in pairs(handlers) do count2 = count2 + 1 end
print("handlers: " .. count .. " " .. count2)
