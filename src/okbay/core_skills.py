"""Combined core-skills auto-start + C1 status (CE + okstratr + wiki_build).

Ben lock: always auto-start CE + okstratr with the okbay session/daemon.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from . import ce_supervisor, okstratr_supervisor, paths

log = logging.getLogger("okbay.core_skills")

_started = False
_lock = threading.Lock()
_poller: threading.Thread | None = None


def status(workspace: Path | None = None) -> dict[str, Any]:
    """Return the C1 status object."""
    ce = ce_supervisor.contract_slice(workspace)
    oks = okstratr_supervisor.contract_slice()
    wiki = ce_supervisor.wiki_build_slice()
    return {
        "ce": ce,
        "okstratr": oks,
        "wiki_build": wiki,
    }


def ensure_started(
    workspace: Path | None = None,
    *,
    keep_alive: bool = True,
    wait_okstratr: bool = False,
) -> dict[str, Any]:
    """Idempotent session auto-start for CE + okstratr.

    Called from ``okbay serve`` / daemon start. CE data/APIs are claimed
    locally (okbayd); okstratr is spawned on :8767. Respects viewer_mutex
    (no HTML atlas host when QML).
    """
    global _started, _poller
    ws = Path(workspace).expanduser() if workspace else paths.workspace()
    with _lock:
        ce_out = ce_supervisor.start(ws)
        # Claim local API immediately so status is not empty while bind races.
        ce_supervisor.claim_local_api()

        if wait_okstratr:
            oks_out = okstratr_supervisor.start(ws)
        else:
            # Non-blocking spawn so serve() can bind :8766 quickly.
            oks_out: dict[str, Any] = {"ok": True, "deferred": True}

            def _spawn() -> None:
                try:
                    out = okstratr_supervisor.start(ws)
                    if not out.get("ok"):
                        log.warning("okstratr auto-start failed: %s", out.get("error"))
                except Exception:  # noqa: BLE001
                    log.exception("okstratr auto-start error")

            threading.Thread(target=_spawn, name="okbay-okstratr-start", daemon=True).start()

        if keep_alive and (_poller is None or not _poller.is_alive()):
            _poller = threading.Thread(
                target=okstratr_supervisor.poll_forever,
                args=(ws,),
                name="okbay-okstratr-supervisor",
                daemon=True,
            )
            _poller.start()

        _started = True
        return {
            "ok": bool(ce_out.get("ok")),
            "ce": ce_out,
            "okstratr": oks_out,
            "status": status(ws),
        }


def reset_for_tests() -> None:
    """Test helper: clear module start latch (does not kill processes)."""
    global _started, _poller
    with _lock:
        _started = False
        _poller = None
