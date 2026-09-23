"""Thin client over okstratr harness+model registry (SSOT).

Ben lock: okstratr owns the harness allowlist and model pools
(``harnesses.toml``). okbay Settings / CLI configure that registry
through HTTP — they must **not** invent a parallel okbay allowlist.

Call paths
----------
* **Daemon thin routes:** ``/api/okstratr/harness`` (and
  ``…/enable|disable|set|reload``) so UI/shells need not know upstream
  paths. Server-side these call ``OKBAY_OKSTRATR_UPSTREAM``
  (default ``http://127.0.0.1:8767``), loopback-guarded, with
  ``X-Okstratr-Host: okbay``.
* **CLI:** ``okbay harness list|enable|disable|set|reload`` (same client).

Mirrors Switchbay ``okstratr_harness`` (ADR-005). okbay has no rich
Settings UI yet — CLI + GET ``/api/okstratr/harness`` are first-class
for bare-adjacent Omarchy users. See ``docs/HERDR-AND-REGISTRY.md``.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import os
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

log = logging.getLogger("okbay.okstratr_harness")

HOST_HEADER = "X-Okstratr-Host"
HOSTED_SHELL = "okbay"
_DEFAULT_UPSTREAM = "http://127.0.0.1:8767"
_ENV_UPSTREAM = "OKBAY_OKSTRATR_UPSTREAM"

# Upstream okstratr paths (also available under /api/config/harness…).
_PATHS = {
    "list": "/api/harness",
    "enable": "/api/harness/enable",
    "disable": "/api/harness/disable",
    "set": "/api/harness/set",
    "reload": "/api/harness/reload",
}

# Same-origin embed prefixes (when a proxy exists; Switchbay parity).
EMBED_LIST = "/embed/okstratr/api/harness"
EMBED_ENABLE = "/embed/okstratr/api/harness/enable"
EMBED_DISABLE = "/embed/okstratr/api/harness/disable"
EMBED_SET = "/embed/okstratr/api/harness/set"
EMBED_RELOAD = "/embed/okstratr/api/harness/reload"

# okbay daemon façades (preferred for this shell).
DAEMON_LIST = "/api/okstratr/harness"
DAEMON_ENABLE = "/api/okstratr/harness/enable"
DAEMON_DISABLE = "/api/okstratr/harness/disable"
DAEMON_SET = "/api/okstratr/harness/set"
DAEMON_RELOAD = "/api/okstratr/harness/reload"


class OkstratrHarnessError(RuntimeError):
    """Upstream unreachable, non-loopback, or bad response."""

    def __init__(self, message: str, *, status: int = 502, detail: Any = None):
        super().__init__(message)
        self.status = status
        self.detail = detail


class UpstreamNotLoopback(OkstratrHarnessError):
    """Raised when OKBAY_OKSTRATR_UPSTREAM is not loopback."""

    def __init__(self, message: str):
        super().__init__(message, status=502)


def embed_paths() -> dict[str, str]:
    """Public same-origin paths (for docs / UI hints; Switchbay parity)."""
    return {
        "list": EMBED_LIST,
        "enable": EMBED_ENABLE,
        "disable": EMBED_DISABLE,
        "set": EMBED_SET,
        "reload": EMBED_RELOAD,
    }


def daemon_paths() -> dict[str, str]:
    """okbay path-native façades (preferred when no embed proxy)."""
    return {
        "list": DAEMON_LIST,
        "enable": DAEMON_ENABLE,
        "disable": DAEMON_DISABLE,
        "set": DAEMON_SET,
        "reload": DAEMON_RELOAD,
    }


def _normalize_base(url: str) -> str:
    u = (url or "").rstrip("/")
    if "://" not in u:
        u = "http://" + u
    return u


def is_loopback_host(host: str) -> bool:
    """True iff *host* (no port) is a loopback literal."""
    h = (host or "").strip().lower()
    if h in ("localhost", "127.0.0.1", "::1"):
        return True
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1]
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def assert_loopback_upstream(url: str) -> str:
    """Validate upstream URL is http(s) to a loopback host. Return base."""
    base = _normalize_base(url)
    parts = urlsplit(base)
    if parts.scheme not in ("http", "https"):
        raise UpstreamNotLoopback(f"okstratr upstream scheme must be http(s): {url!r}")
    host = parts.hostname or ""
    if not is_loopback_host(host):
        raise UpstreamNotLoopback(
            f"okstratr upstream must be loopback-only (got host {host!r} from {url!r})"
        )
    return urlunsplit((parts.scheme, parts.netloc, "", "", "")).rstrip("/")


def okstratr_upstream() -> str:
    raw = (os.environ.get(_ENV_UPSTREAM) or "").strip()
    return assert_loopback_upstream(raw or _DEFAULT_UPSTREAM)


def upstream_url(action: str = "list") -> str:
    """Absolute loopback URL for a harness API action."""
    path = _PATHS.get(action)
    if path is None:
        raise ValueError(f"unknown harness action: {action!r}")
    try:
        base = okstratr_upstream()
    except UpstreamNotLoopback as e:
        raise OkstratrHarnessError(str(e), status=502) from e
    return f"{base}{path}"


def normalize_registry(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Map okstratr ``list_for_api`` JSON into a stable okbay view.

    Pass-through of the SSOT fields; never invents an allowlist. Missing
    keys become empty defaults so CLI/UI can render safely.
    """
    raw = dict(payload or {})
    harnesses_in = raw.get("harnesses")
    rows: list[dict[str, Any]] = []
    if isinstance(harnesses_in, list):
        for item in harnesses_in:
            if not isinstance(item, dict):
                continue
            hid = str(item.get("id") or "").strip().lower()
            if not hid:
                continue
            models = item.get("models") or []
            if not isinstance(models, list):
                models = []
            effort = item.get("effort") if isinstance(item.get("effort"), dict) else {}
            settings = (
                item.get("settings") if isinstance(item.get("settings"), dict) else {}
            )
            rows.append(
                {
                    "id": hid,
                    "label": str(item.get("label") or hid),
                    "enabled": bool(item.get("enabled")),
                    "installed": bool(item.get("installed")),
                    "default_model": item.get("default_model"),
                    "models": [str(m) for m in models],
                    "effort": dict(effort),
                    "settings": dict(settings),
                    "herdr_kind": item.get("herdr_kind"),
                    "bin_names": list(item.get("bin_names") or []),
                    "notes": str(item.get("notes") or ""),
                }
            )
    enabled = raw.get("enabled")
    if not isinstance(enabled, list):
        enabled = [h["id"] for h in rows if h["enabled"]]
    preference = raw.get("preference")
    if not isinstance(preference, list):
        preference = list(enabled)
    defaults = raw.get("defaults") if isinstance(raw.get("defaults"), dict) else {}
    blackboard = (
        raw.get("blackboard") if isinstance(raw.get("blackboard"), dict) else {}
    )
    return {
        "ok": bool(raw.get("ok", True)),
        "ssot": "okstratr",
        "host": HOSTED_SHELL,
        "path": raw.get("path"),
        "enabled": [str(x).strip().lower() for x in enabled if str(x).strip()],
        "preference": [str(x).strip().lower() for x in preference if str(x).strip()],
        "defaults": dict(defaults),
        "backend": str(raw.get("backend") or defaults.get("backend") or ""),
        "harnesses": rows,
        "blackboard": dict(blackboard),
        "embed_paths": embed_paths(),
        "daemon_paths": daemon_paths(),
    }


def _hosted_headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        HOST_HEADER: HOSTED_SHELL,
    }


def call_harness(
    action: str,
    *,
    method: str = "GET",
    body: Mapping[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """HTTP call to okstratr harness API; return normalized registry."""
    url = upstream_url(action)
    data = None
    if body is not None or method.upper() != "GET":
        data = json.dumps(dict(body) if body is not None else {}).encode("utf-8")
    req = Request(url, data=data, headers=_hosted_headers(), method=method.upper())
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — loopback-guarded
            raw = resp.read().decode("utf-8", errors="replace")
            status = int(getattr(resp, "status", 200) or 200)
            try:
                parsed = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError as e:
                raise OkstratrHarnessError(
                    f"okstratr harness returned non-JSON (HTTP {status})",
                    status=502 if status >= 500 else status,
                    detail=raw[:500],
                ) from e
            if status >= 400:
                err = None
                if isinstance(parsed, dict):
                    err = parsed.get("error") or parsed.get("detail")
                raise OkstratrHarnessError(
                    str(err or f"okstratr harness HTTP {status}"),
                    status=status,
                    detail=parsed,
                )
            if not isinstance(parsed, dict):
                raise OkstratrHarnessError(
                    "okstratr harness response must be a JSON object",
                    status=502,
                    detail=parsed,
                )
            if action == "reload" and isinstance(parsed.get("config"), dict):
                return normalize_registry(parsed["config"])
            return normalize_registry(parsed)
    except OkstratrHarnessError:
        raise
    except HTTPError as e:
        try:
            raw = e.read().decode("utf-8", errors="replace")
            parsed: Any = json.loads(raw) if raw.strip() else {}
        except Exception:  # noqa: BLE001
            parsed = None
            raw = str(e)
        err = None
        if isinstance(parsed, dict):
            err = parsed.get("error") or parsed.get("detail")
        raise OkstratrHarnessError(
            str(err or f"okstratr harness HTTP {e.code}"),
            status=int(e.code or 502),
            detail=parsed if parsed is not None else raw[:500],
        ) from e
    except (URLError, OSError, TimeoutError) as e:
        log.warning("okstratr harness unreachable %s: %s", url, e)
        raise OkstratrHarnessError(
            "okstratr harness unreachable (is okstratr up on OKBAY_OKSTRATR_UPSTREAM?)",
            status=502,
            detail=str(e),
        ) from e
    except Exception as e:  # noqa: BLE001
        log.exception("okstratr harness call failed for %s", url)
        raise OkstratrHarnessError(
            f"okstratr harness call failed: {e}",
            status=502,
            detail=str(e),
        ) from e


def list_harnesses(*, timeout: float = 30.0) -> dict[str, Any]:
    return call_harness("list", method="GET", timeout=timeout)


def enable_harness(harness_id: str, *, timeout: float = 30.0) -> dict[str, Any]:
    hid = (harness_id or "").strip()
    if not hid:
        raise OkstratrHarnessError("id is required", status=400)
    return call_harness("enable", method="POST", body={"id": hid}, timeout=timeout)


def disable_harness(harness_id: str, *, timeout: float = 30.0) -> dict[str, Any]:
    hid = (harness_id or "").strip()
    if not hid:
        raise OkstratrHarnessError("id is required", status=400)
    return call_harness("disable", method="POST", body={"id": hid}, timeout=timeout)


def set_harness_value(
    key: str, value: str, *, timeout: float = 30.0
) -> dict[str, Any]:
    k = (key or "").strip()
    if not k:
        raise OkstratrHarnessError("key is required", status=400)
    return call_harness(
        "set",
        method="POST",
        body={"key": k, "value": "" if value is None else str(value)},
        timeout=timeout,
    )


def reload_harnesses(*, timeout: float = 30.0) -> dict[str, Any]:
    return call_harness("reload", method="POST", body={}, timeout=timeout)


def error_payload(exc: OkstratrHarnessError) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "ssot": "okstratr",
        "host": HOSTED_SHELL,
        "error": str(exc),
    }
    if exc.detail is not None:
        payload["detail"] = exc.detail
    return payload


def status_hint() -> dict[str, Any]:
    """Cheap status pointer (no network) for ``okbay status`` / ``/api/status``."""
    try:
        upstream = okstratr_upstream()
    except OkstratrHarnessError as e:
        upstream = str(e)
    return {
        "ssot": "okstratr",
        "host": HOSTED_SHELL,
        "upstream": upstream,
        "api": DAEMON_LIST,
        "cli": "okbay harness list|enable|disable|set|reload",
        "daemon_paths": daemon_paths(),
    }


__all__ = [
    "HOST_HEADER",
    "HOSTED_SHELL",
    "OkstratrHarnessError",
    "UpstreamNotLoopback",
    "embed_paths",
    "daemon_paths",
    "is_loopback_host",
    "assert_loopback_upstream",
    "okstratr_upstream",
    "upstream_url",
    "normalize_registry",
    "call_harness",
    "list_harnesses",
    "enable_harness",
    "disable_harness",
    "set_harness_value",
    "reload_harnesses",
    "error_payload",
    "status_hint",
]
