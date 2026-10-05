"""CE availability for okbay sessions (core skill).

Contract C1 (okbay row): start CE viewer when the HTML path needs it; when QML
is active, still keep CE **data/APIs** available and do **not** open the HTML
atlas host (viewer_mutex).

Today okbay itself is the CE data plane on ``:8766`` (graph / atlas JSON).
Charter end-state may move HTTP to a standalone CE process; until then this
supervisor:

* Marks CE healthy when the local okbay API (``OKBAY_CE_UPSTREAM``, default
  ``http://127.0.0.1:8766``) answers ``/health``.
* Never spawns / opens an HTML atlas surface when ``viewer_mode=qml``.
* Optionally spawns external ``viewer.sh serve`` only when HTML mode **and**
  ``OKBAY_CE_EXTERNAL_VIEWER=1`` (side port ``OKBAY_CE_VIEWER_PORT``, default
  8090) so it does not collide with okbayd on :8766.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from . import ce, paths, viewer_mutex

log = logging.getLogger("okbay.ce_supervisor")

_PID_NAME = "ce-viewer.pid"
_LOG_NAME = "ce-viewer.log"
_DEFAULT_UPSTREAM = "http://127.0.0.1:8766"
_DEFAULT_EXTERNAL_PORT = 8090

_CE_STATE: dict[str, str] = {"state": "stopped", "detail": ""}
_WIKI_BUILD: dict[str, object] = {
    "state": "idle",  # idle|building|failed
    "pages": None,
    "detail": "",
}
# True once session autostart has claimed the local okbay API as CE SSOT.
_LOCAL_API_CLAIMED = False


def _set_ce_state(state: str, detail: str = "") -> None:
    _CE_STATE["state"] = state
    _CE_STATE["detail"] = detail


def _set_wiki_build(state: str, *, pages=None, detail: str = "") -> None:
    _WIKI_BUILD["state"] = state
    _WIKI_BUILD["pages"] = pages
    _WIKI_BUILD["detail"] = detail


def _state_dir() -> Path:
    d = paths.state_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def pid_path() -> Path:
    return _state_dir() / _PID_NAME


def log_path() -> Path:
    return _state_dir() / _LOG_NAME


def upstream_base() -> str:
    raw = (os.environ.get("OKBAY_CE_UPSTREAM") or "").strip()
    return (raw or _DEFAULT_UPSTREAM).rstrip("/")


def upstream_port() -> int:
    u = urlparse(upstream_base())
    if u.port:
        return int(u.port)
    return 443 if u.scheme == "https" else 80


def health_url() -> str:
    return upstream_base() + "/health"


def html_viewer_allowed(mode: str | None = None) -> bool:
    """False when QML owns the viewer (mutex) — do not open HTML atlas host."""
    return viewer_mutex.html_ui_enabled(mode)  # type: ignore[arg-type]


def external_viewer_requested() -> bool:
    raw = (os.environ.get("OKBAY_CE_EXTERNAL_VIEWER") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def external_viewer_port() -> int:
    raw = (os.environ.get("OKBAY_CE_VIEWER_PORT") or "").strip()
    if raw.isdigit():
        return int(raw)
    return _DEFAULT_EXTERNAL_PORT


def is_healthy(*, timeout: float = 2.0) -> bool:
    """True when CE data/API upstream answers (okbayd :8766 by default)."""
    if _LOCAL_API_CLAIMED and upstream_base() == _DEFAULT_UPSTREAM.rstrip("/"):
        # We are (or will be) the listening okbayd process — claim counts as healthy
        # for contract status once session start ran.
        if _CE_STATE.get("state") in {"healthy", "starting"}:
            if _CE_STATE.get("state") == "healthy":
                return True
    try:
        with urlopen(health_url(), timeout=timeout) as resp:  # noqa: S310 — loopback
            return 200 <= int(getattr(resp, "status", 200)) < 500
    except (URLError, OSError, TimeoutError, ValueError):
        return False


def claim_local_api(*, detail: str = "okbay API (CE SSOT)") -> None:
    """Called from okbayd serve: this process *is* the CE data plane."""
    global _LOCAL_API_CLAIMED
    _LOCAL_API_CLAIMED = True
    mode = viewer_mutex.resolve_mode()
    if html_viewer_allowed(mode):
        _set_ce_state("healthy", f"{detail}; html atlas routes on")
    else:
        _set_ce_state(
            "healthy",
            f"{detail}; qml mode — HTML atlas host off, APIs on",
        )


def _read_pid() -> int | None:
    p = pid_path()
    if not p.is_file():
        return None
    try:
        raw = p.read_text(encoding="utf-8").strip()
        return int(raw) if raw else None
    except (OSError, ValueError):
        return None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def contract_slice(workspace: Path | None = None) -> dict[str, Any]:
    """C1 status slice for CE."""
    healthy = is_healthy()
    pid = _read_pid()
    if healthy:
        state = "healthy"
        detail = _CE_STATE.get("detail") or "up"
    elif _CE_STATE.get("state") == "starting":
        state = "starting"
        detail = _CE_STATE.get("detail") or "starting"
    elif pid and _pid_alive(pid):
        state = "unhealthy"
        detail = _CE_STATE.get("detail") or "process up but health failing"
    elif _CE_STATE.get("state") == "unhealthy":
        state = "unhealthy"
        detail = _CE_STATE.get("detail") or "unhealthy"
    else:
        state = "stopped"
        detail = _CE_STATE.get("detail") or "stopped"
    out = {
        "state": state,
        "url": upstream_base(),
        "detail": detail,
    }
    if workspace is not None:
        out["workspace"] = str(workspace)
    out["html_viewer_allowed"] = html_viewer_allowed()
    out["viewer_mode"] = viewer_mutex.resolve_mode()
    return out


def wiki_build_slice() -> dict[str, Any]:
    return {
        "state": str(_WIKI_BUILD.get("state") or "idle"),
        "pages": _WIKI_BUILD.get("pages"),
        "detail": str(_WIKI_BUILD.get("detail") or ""),
    }


def _ensure_workspace_data(workspace: Path) -> dict[str, Any]:
    """Make sure wiki/graph APIs have something to serve."""
    workspace = Path(workspace).expanduser()
    wiki = workspace / "wiki"
    notes: list[str] = []
    if not wiki.is_dir():
        return {"ok": True, "wiki": False, "notes": ["no wiki/ yet"]}
    try:
        from . import status as status_mod

        snap = status_mod.compute(workspace)
        pages = snap.get("pages")
        _set_wiki_build("idle", pages=pages, detail="status warm")
        notes.append(f"pages={pages}")
    except Exception as e:  # noqa: BLE001
        _set_wiki_build("failed", detail=str(e))
        notes.append(f"status warm failed: {e}")
    return {"ok": True, "wiki": True, "notes": notes}


def _spawn_external_viewer(workspace: Path) -> dict[str, Any]:
    """Optional CE viewer.sh on a side port (HTML mode only)."""
    if not html_viewer_allowed():
        return {
            "ok": False,
            "skipped": True,
            "error": "html_ui_disabled",
            "detail": "QML mode — refusing external HTML viewer spawn",
        }
    root = ce.ce_root()
    if root is None:
        return {"ok": False, "error": "CE root not found", "hint": "set OKBAY_CE_ROOT"}
    script = root / "scripts" / "viewer.sh"
    if not script.is_file():
        return {"ok": False, "error": f"viewer.sh missing under {root}"}
    if not (workspace / "wiki").is_dir():
        return {"ok": False, "error": f"no wiki/ under {workspace}"}

    port = external_viewer_port()
    old = _read_pid()
    if old and not _pid_alive(old):
        try:
            pid_path().unlink(missing_ok=True)
        except OSError:
            pass

    env = os.environ.copy()
    logf = log_path().open("a", encoding="utf-8")
    try:
        proc = subprocess.Popen(  # noqa: S603
            ["bash", str(script), "serve", str(port)],
            cwd=str(workspace),
            env=env,
            stdout=logf,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except OSError as e:
        logf.close()
        return {"ok": False, "error": f"failed to spawn viewer: {e}"}

    try:
        pid_path().write_text(str(proc.pid) + "\n", encoding="utf-8")
    except OSError as e:
        log.warning("could not write ce-viewer pid: %s", e)

    return {
        "ok": True,
        "pid": proc.pid,
        "port": port,
        "url": f"http://127.0.0.1:{port}",
        "log": str(log_path()),
        "argv": ["bash", str(script), "serve", str(port)],
    }


def start(workspace: Path | None = None) -> dict[str, Any]:
    """Ensure CE data/APIs (and optional HTML viewer) for a session. Idempotent."""
    ws = Path(workspace).expanduser() if workspace else paths.workspace()
    mode = viewer_mutex.resolve_mode()
    _set_ce_state("starting", f"session start viewer_mode={mode}")

    data = _ensure_workspace_data(ws)
    html_ok = html_viewer_allowed(mode)

    result: dict[str, Any] = {
        "ok": True,
        "workspace": str(ws),
        "viewer_mode": mode,
        "html_viewer_allowed": html_ok,
        "html_atlas_host": html_ok,  # okbay serves /atlas only when mutex allows
        "apis": True,
        "ce_tooling": ce.available(),
        "ce_root": str(ce.ce_root()) if ce.ce_root() else None,
        "data": data,
        "url": upstream_base(),
    }

    if not html_ok:
        # QML: backends/APIs only — never open HTML atlas host.
        claim_local_api(detail="okbay API (CE SSOT)")
        result["detail"] = "qml: CE APIs on; HTML atlas host off"
        result["external_viewer"] = {"ok": False, "skipped": True, "reason": "qml_mutex"}
        return result

    # HTML path: atlas host is this daemon's /atlas routes (mutex on).
    # Optional side-port CE viewer.sh when explicitly requested.
    if external_viewer_requested():
        ext = _spawn_external_viewer(ws)
        result["external_viewer"] = ext
        if not ext.get("ok") and not ext.get("skipped"):
            _set_ce_state("unhealthy", str(ext.get("error") or "external viewer failed"))
            result["ok"] = False
            result["error"] = ext.get("error")
            return result
    else:
        result["external_viewer"] = {
            "ok": True,
            "skipped": True,
            "reason": "okbay HTML atlas is CE viewer surface (set OKBAY_CE_EXTERNAL_VIEWER=1 for viewer.sh)",
        }

    claim_local_api(detail="okbay API (CE SSOT)")
    result["detail"] = "html: CE APIs + atlas host via okbayd"
    # If upstream already answers, refine state.
    if is_healthy():
        _set_ce_state("healthy", result["detail"])
    return result


def stop_external_viewer() -> dict[str, Any]:
    pid = _read_pid()
    if not pid:
        return {"ok": True, "stopped": False, "note": "no pid file"}
    if not _pid_alive(pid):
        try:
            pid_path().unlink(missing_ok=True)
        except OSError:
            pass
        return {"ok": True, "stopped": False, "note": "pid gone", "pid": pid}
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as e:
        try:
            pid_path().unlink(missing_ok=True)
        except OSError:
            pass
        return {"ok": True, "stopped": False, "note": f"pid gone: {e}", "pid": pid}
    deadline = time.time() + 5.0
    while time.time() < deadline and _pid_alive(pid):
        time.sleep(0.2)
    if _pid_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        pid_path().unlink(missing_ok=True)
    except OSError:
        pass
    return {"ok": True, "stopped": True, "pid": pid}


def status(workspace: Path | None = None) -> dict[str, Any]:
    pid = _read_pid()
    return {
        "ok": True,
        "healthy": is_healthy(),
        "url": upstream_base(),
        "port": upstream_port(),
        "pid": pid,
        "pid_alive": _pid_alive(pid) if pid else False,
        "html_viewer_allowed": html_viewer_allowed(),
        "viewer_mode": viewer_mutex.resolve_mode(),
        "ce_tooling": ce.available(),
        "workspace": str(workspace) if workspace else None,
        "log": str(log_path()),
        "contract": contract_slice(workspace),
        "wiki_build": wiki_build_slice(),
    }
