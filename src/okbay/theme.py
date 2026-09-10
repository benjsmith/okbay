"""Resolve Omarchy system theme colors for Atlas and QML surfaces."""
from __future__ import annotations
import os, time
from pathlib import Path

SWITCHBAY_TYPE = {
    "project": "#4d1ae8", "projects": "#4d1ae8",
    "analysis": "#1d6996", "analyses": "#1d6996",
    "concept": "#38a6a5", "concepts": "#38a6a5",
    "entity": "#0f8554", "entities": "#0f8554",
    "evidence": "#73af48",
    "fact": "#edad08", "facts": "#edad08",
    "figure": "#e17c05", "figures": "#e17c05",
    "table": "#cc503e", "tables": "#cc503e",
    "source": "#94346e", "sources": "#94346e",
    "note": "#6f4070", "notes": "#6f4070",
    "todo": "#9656a2", "todo-list": "#9656a2",
    "hub": "#6be8b3", "unclassified": "#ffffff",
    "missing": "#5a6068", "default": "#9aa0a8",
}
SWITCHBAY_CHROME = {
    "mode": "dark", "accent": "#6be8b3", "selection": "#1f242c", "muted": "#343942",
    "background": "#0f1115", "dark_background": "#0b0d10", "darker_background": "#07080a",
    "lighter_background": "#161a21", "foreground": "#e6e8eb", "dark_foreground": "#5a6068",
    "light_foreground": "#c5c9ce", "bright_foreground": "#f4f6f8",
    "red": "#cc503e", "yellow": "#edad08", "orange": "#e17c05", "green": "#0f8554",
    "cyan": "#38a6a5", "blue": "#1d6996", "magenta": "#94346e", "brown": "#6f4070",
    "bright_red": "#e17c05", "bright_yellow": "#edad08", "bright_green": "#73af48",
    "bright_cyan": "#6be8b3", "bright_blue": "#4d1ae8", "bright_magenta": "#9656a2",
}
KIND_TO_NAMED = {
    "project": "bright_blue", "projects": "bright_blue",
    "analysis": "blue", "analyses": "blue",
    "concept": "cyan", "concepts": "cyan",
    "entity": "green", "entities": "green",
    "evidence": "bright_green", "fact": "yellow", "facts": "yellow",
    "figure": "orange", "figures": "orange",
    "table": "red", "tables": "red",
    "source": "magenta", "sources": "magenta",
    "note": "brown", "notes": "brown",
    "todo": "bright_magenta", "todo-list": "bright_magenta",
    "hub": "accent", "unclassified": "bright_foreground",
    "missing": "muted", "default": "dark_foreground",
}

def _home() -> Path:
    return Path(os.environ.get("HOME") or Path.home())

def omarchy_state_root() -> Path:
    raw = os.environ.get("XDG_STATE_HOME")
    state = Path(raw) if raw else _home() / ".local" / "state"
    return state / "omarchy" / "current"

def theme_name() -> str:
    for candidate in (omarchy_state_root() / "theme.name", _home() / ".config" / "omarchy" / "current" / "theme.name"):
        if candidate.is_file():
            name = candidate.read_text(encoding="utf-8").strip()
            if name:
                return name
    return ""

def colors_toml_path() -> Path | None:
    for p in (
        omarchy_state_root() / "theme" / "colors.toml",
        omarchy_state_root() / "next-theme" / "colors.toml",
        _home() / ".config" / "omarchy" / "current" / "theme" / "colors.toml",
        _home() / ".config" / "omarchy" / "themes" / "switchbay" / "colors.toml",
    ):
        if p.is_file():
            return p
    return None

def parse_toml_colors(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and val:
            out[key] = val
    return out

def load_omarchy_colors() -> dict[str, str]:
    path = colors_toml_path()
    merged = dict(SWITCHBAY_CHROME)
    if path is None:
        return merged
    try:
        merged.update(parse_toml_colors(path.read_text(encoding="utf-8")))
    except OSError:
        pass
    return merged

def _kind_color(colors: dict[str, str], kind: str) -> str:
    kind = (kind or "default").lower().replace(" ", "-")
    explicit = colors.get(f"type_{kind}") or colors.get(f"type-{kind}")
    if explicit:
        return explicit
    named = KIND_TO_NAMED.get(kind)
    if named and colors.get(named):
        return colors[named]
    return SWITCHBAY_TYPE.get(kind) or colors.get("dark_foreground") or SWITCHBAY_TYPE["default"]

def type_palette(colors=None):
    colors = colors or load_omarchy_colors()
    kinds = set(SWITCHBAY_TYPE) | set(KIND_TO_NAMED)
    return {kind: _kind_color(colors, kind) for kind in kinds}

def atlas_theme() -> dict:
    colors = load_omarchy_colors()
    types = type_palette(colors)
    path = colors_toml_path()
    return {
        "name": theme_name() or "switchbay-fallback",
        "source": str(path) if path else "",
        "mode": colors.get("mode", "dark"),
        "chrome": {k: colors.get(k, SWITCHBAY_CHROME.get(k, "")) for k in SWITCHBAY_CHROME if k != "mode"},
        "types": types,
        "ts": time.time(),
    }

def resolve() -> dict:
    theme = atlas_theme()
    theme["kinds"] = theme.get("types") or {}
    theme["theme"] = theme.get("name") or "switchbay-fallback"
    chrome = theme.get("chrome") or {}
    theme["accent"] = chrome.get("accent", "#6be8b3")
    theme["background"] = chrome.get("background", "#0f1115")
    theme["foreground"] = chrome.get("foreground", "#e6e8eb")
    return theme

def kind_colors(colors=None):
    return type_palette(colors)
