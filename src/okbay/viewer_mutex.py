"""HTML vs QML viewer mutex (charter Phase 5a).

Charter locked decision #3: okbay QML active ⇒ HTML atlas/observer hosts **off**
(single viewer route). JSON APIs on :8766 stay up either way.

Resolution order (highest wins):
1. ``OKBAY_VIEWER_MODE`` env (``html`` | ``qml``)
2. ``~/.config/okbay/viewer.json`` ``{"mode": "html"|"qml"}``
3. default ``html`` (today's Chromium ``--app=/atlas`` path)

When mode is ``qml``, HTML UI routes (``/``, ``/atlas``, ``/views/*``) are
suppressed; callers get 409 + a small HTML stub. ``/api/*``, ``/health``,
``/static/*`` remain available for QML and agents.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from . import paths

ViewerMode = Literal["html", "qml"]
_VALID = frozenset({"html", "qml"})

# HTML surface paths that duplicate QML Atlas / panel chrome.
HTML_UI_PATHS = frozenset({"/", "/atlas"})


def viewer_config_path() -> Path:
    return paths.config_dir() / "viewer.json"


def _normalize(raw: str | None) -> ViewerMode | None:
    if not raw:
        return None
    mode = str(raw).strip().lower()
    if mode in _VALID:
        return mode  # type: ignore[return-value]
    return None


def load_config_mode() -> ViewerMode | None:
    p = viewer_config_path()
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return _normalize(data.get("mode") or data.get("viewer_mode"))


def set_mode(mode: str, *, source: str = "cli") -> dict[str, Any]:
    """Persist viewer mode to config (does not override a set env var at runtime)."""
    normalized = _normalize(mode)
    if normalized is None:
        raise ValueError("mode must be 'html' or 'qml'")
    dest = viewer_config_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {"mode": normalized, "source": source}
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(dest)
    return snapshot()


def resolve_mode() -> ViewerMode:
    env = _normalize(os.environ.get("OKBAY_VIEWER_MODE"))
    if env is not None:
        return env
    cfg = load_config_mode()
    if cfg is not None:
        return cfg
    return "html"


def html_ui_enabled(mode: ViewerMode | None = None) -> bool:
    """True when HTML atlas / views hosts may serve full UI."""
    return (mode or resolve_mode()) == "html"


def is_html_ui_path(path: str) -> bool:
    """Return True for routes that are HTML viewer surfaces (not JSON API)."""
    if not path:
        return False
    # strip query already; path only
    if path in HTML_UI_PATHS:
        return True
    if path.startswith("/views/"):
        return True
    return False


def should_block_html_ui(path: str, mode: ViewerMode | None = None) -> bool:
    """Mutex gate: block HTML UI when QML is the active viewer."""
    if html_ui_enabled(mode):
        return False
    return is_html_ui_path(path)


def blocked_payload(path: str, mode: ViewerMode | None = None) -> dict[str, Any]:
    m = mode or resolve_mode()
    return {
        "ok": False,
        "error": "html_ui_disabled",
        "message": (
            "QML viewer mode is active; HTML atlas/observer hosts are off "
            "(charter: single viewer route). Use Omarchy QML panels or JSON API."
        ),
        "path": path,
        "viewer_mode": m,
        "html_ui_enabled": False,
        "api_url": "http://127.0.0.1:8766",
        "hint": "okbay viewer set html  # restore Chromium /atlas host",
    }


def blocked_html_stub(path: str, mode: ViewerMode | None = None) -> str:
    body = blocked_payload(path, mode)
    return (
        "<!doctype html><html><head><meta charset=utf-8>"
        "<title>OKBay — HTML UI off</title></head><body>"
        "<h1>HTML atlas host off</h1>"
        f"<p>{body['message']}</p>"
        f"<p>viewer_mode=<code>{body['viewer_mode']}</code> · "
        f"path=<code>{path}</code></p>"
        "<p>JSON API remains on <code>http://127.0.0.1:8766</code>.</p>"
        "</body></html>"
    )


def snapshot() -> dict[str, Any]:
    mode = resolve_mode()
    env_set = _normalize(os.environ.get("OKBAY_VIEWER_MODE")) is not None
    return {
        "viewer_mode": mode,
        "html_ui_enabled": html_ui_enabled(mode),
        "config_path": str(viewer_config_path()),
        "env_override": env_set,
        "html_ui_paths": sorted(HTML_UI_PATHS) + ["/views/*"],
        "policy": "qml_active_implies_html_atlas_off",
    }
