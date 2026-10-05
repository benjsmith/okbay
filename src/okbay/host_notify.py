"""Map okstratr ``host_notify`` envelopes onto Herdr-visible I/O.

Contract C2: okbay / Omarchy sink is **Herdr only** (path-native). okstratr
emits ``okstratr.host_notify`` v1; this host validates and forwards to the
Herdr bridge stub:

1. Append one JSON line to ``~/.local/state/okbay/herdr-notify.jsonl``
   (override with ``OKBAY_HERDR_NOTIFY_LOG``).
2. Print a short ``herdr:``-prefixed line on stderr for live tails / panes.

Herdr (or a future bridge) tails the JSONL. There is no OS notify / second
inbox on this path. See ``docs/HERDR-AND-REGISTRY.md``.

Default POST target when ``OKSTRATR_HOST=okbay``:
``http://127.0.0.1:8766/api/okstratr/host-notify`` (okstratr ADR-005).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, TextIO

from . import paths

ENVELOPE_TYPE = "okstratr.host_notify"
ENVELOPE_V = 1

KINDS = frozenset(
    {
        "schedule.start",
        "schedule.progress",
        "schedule.done",
        "schedule.failed",
        "desk.progress",
        "desk.done",
    }
)

_KIND_LABELS = {
    "schedule.start": "Schedule started",
    "schedule.progress": "Schedule progress",
    "schedule.done": "Schedule done",
    "schedule.failed": "Schedule failed",
    "desk.progress": "Desk progress",
    "desk.done": "Desk done",
}

ENV_NOTIFY_LOG = "OKBAY_HERDR_NOTIFY_LOG"


class HostNotifyError(ValueError):
    """Invalid host_notify envelope."""


def herdr_notify_log_path() -> Path:
    """Well-known JSONL Herdr tails (or a future bridge)."""
    override = (os.environ.get(ENV_NOTIFY_LOG) or "").strip()
    if override:
        return Path(override).expanduser()
    return paths.state_dir() / "herdr-notify.jsonl"


def validate_envelope(body: Any) -> dict[str, Any]:
    """Validate and return a normalized envelope copy. Raises HostNotifyError."""
    if not isinstance(body, dict):
        raise HostNotifyError("envelope must be a JSON object")
    if body.get("type") != ENVELOPE_TYPE:
        raise HostNotifyError(f"type must be {ENVELOPE_TYPE!r}")
    try:
        v = int(body.get("v", ENVELOPE_V))
    except (TypeError, ValueError) as e:
        raise HostNotifyError(f"unsupported envelope v={body.get('v')!r}") from e
    if v != ENVELOPE_V:
        raise HostNotifyError(f"unsupported envelope v={v!r}")
    kind = str(body.get("kind") or "").strip()
    if kind not in KINDS:
        raise HostNotifyError(f"kind must be one of {sorted(KINDS)}")
    title = str(body.get("title") or "").strip()
    if not title:
        raise HostNotifyError("title required")
    prog = body.get("progress")
    if prog is None:
        prog = {}
    elif not isinstance(prog, dict):
        raise HostNotifyError("progress must be object")
    desk = body.get("desk")
    if desk in ("", "null", "none"):
        desk = None
    return {
        "type": ENVELOPE_TYPE,
        "v": ENVELOPE_V,
        "kind": kind,
        "schedule_id": body.get("schedule_id"),
        "desk": desk,
        "title": title,
        "body": str(body.get("body") or ""),
        "progress": {
            "pct": prog.get("pct"),
            "phase": str(prog.get("phase") or ""),
            "detail": str(prog.get("detail") or ""),
        },
        "ts": str(body.get("ts") or ""),
    }


def format_herdr_line(envelope: dict[str, Any]) -> str:
    """One short human line: title + optional body (Herdr-visible)."""
    kind = str(envelope.get("kind") or "")
    label = _KIND_LABELS.get(kind, kind)
    title = (envelope.get("title") or "").strip()
    body = (envelope.get("body") or "").strip()
    desk = envelope.get("desk")
    schedule_id = envelope.get("schedule_id")
    progress = envelope.get("progress") if isinstance(envelope.get("progress"), dict) else {}

    head = f"{label}: {title}" if title else label
    meta: list[str] = []
    if desk not in (None, "", "null"):
        meta.append(f"desk={desk}")
    if schedule_id:
        meta.append(f"id={schedule_id}")
    pct = progress.get("pct") if progress else None
    phase = (progress.get("phase") or "") if progress else ""
    if pct is not None:
        meta.append(f"{pct}%")
    if phase:
        meta.append(str(phase))
    bits = [head]
    if meta:
        bits.append("(" + ", ".join(meta) + ")")
    if body:
        bits.append("— " + body)
    return " ".join(bits)


def herdr_record(envelope: dict[str, Any]) -> dict[str, Any]:
    """Structured record written to the JSONL bridge."""
    line = format_herdr_line(envelope)
    return {
        "sink": "herdr",
        "v": 1,
        "text": line,
        "title": envelope.get("title"),
        "body": envelope.get("body") or "",
        "kind": envelope.get("kind"),
        "schedule_id": envelope.get("schedule_id"),
        "desk": envelope.get("desk"),
        "progress": envelope.get("progress"),
        "ts": envelope.get("ts"),
        "envelope": envelope,
    }


def append_herdr_log(record: dict[str, Any], *, path: Path | None = None) -> Path:
    """Append one JSON line to the Herdr notify log."""
    target = path or herdr_notify_log_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str, separators=(",", ":")) + "\n")
    return target


def print_herdr_stderr(line: str, *, stream: TextIO | None = None) -> None:
    """Live Herdr-visible prefix on stderr (or override stream in tests)."""
    out = stream if stream is not None else sys.stderr
    print(f"herdr: {line}", file=out, flush=True)


def receive(
    envelope: Any,
    *,
    log_path: Path | None = None,
    stderr: TextIO | None = None,
    write_log: bool = True,
    print_stderr: bool = True,
) -> dict[str, Any]:
    """Validate envelope and forward to Herdr stub I/O.

    Returns a result dict suitable for HTTP handlers / CLI.
    """
    try:
        env = validate_envelope(envelope)
    except HostNotifyError as e:
        return {"ok": False, "error": str(e), "sink": "herdr"}

    text = format_herdr_line(env)
    record = herdr_record(env)
    written: Path | None = None
    if write_log:
        written = append_herdr_log(record, path=log_path)
    if print_stderr:
        print_herdr_stderr(text, stream=stderr)

    return {
        "ok": True,
        "sink": "herdr",
        "text": text,
        "title": env.get("title"),
        "body": env.get("body") or "",
        "log": str(written) if written else None,
        "record": record,
    }


def receive_json_text(raw: str, **kwargs: Any) -> dict[str, Any]:
    """Parse JSON text (stdin / CLI arg) and receive."""
    raw = (raw or "").strip()
    if not raw:
        return {"ok": False, "error": "empty input", "sink": "herdr"}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"invalid JSON: {e}", "sink": "herdr"}
    return receive(data, **kwargs)


__all__ = [
    "ENVELOPE_TYPE",
    "ENVELOPE_V",
    "KINDS",
    "ENV_NOTIFY_LOG",
    "HostNotifyError",
    "herdr_notify_log_path",
    "validate_envelope",
    "format_herdr_line",
    "herdr_record",
    "append_herdr_log",
    "print_herdr_stderr",
    "receive",
    "receive_json_text",
]
