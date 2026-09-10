"""Standing desks: curate / work / code / deck. Tiny router, no bandit."""
from __future__ import annotations
import json, time
from pathlib import Path
from . import paths

DESK_KINDS = ("curate", "work", "code", "deck")

def _load(ws: Path | None = None) -> dict:
    p = paths.desks_path(ws)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"active": None, "history": []}

def _save(data: dict, ws: Path | None = None) -> None:
    p = paths.desks_path(ws)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def start(kind: str, objective: str = "", ws: Path | None = None) -> dict:
    kind = kind.lower().strip()
    if kind not in DESK_KINDS:
        raise ValueError(f"unknown desk {kind}; want {DESK_KINDS}")
    data = _load(ws)
    desk = {
        "id": kind,
        "state": "working",
        "objective": objective,
        "seated_at": time.time(),
        "fanout": 2 if kind in {"work", "code"} else 1,
        "layout": {"curate": "n=1", "work": "hsl 2", "code": "hdl", "deck": "web-app"}.get(kind),
    }
    data["active"] = desk
    data["history"].append({"id": kind, "objective": objective, "at": desk["seated_at"]})
    _save(data, ws)
    bb = {"claims": [], "desk": kind, "objective": objective}
    paths.blackboard_path(ws).parent.mkdir(parents=True, exist_ok=True)
    paths.blackboard_path(ws).write_text(json.dumps(bb, indent=2), encoding="utf-8")
    return desk

def stop(kind=None, ws: Path | None = None) -> dict:
    data = _load(ws)
    if data.get("active"):
        data["active"]["state"] = "quiet"
    _save(data, ws)
    return data.get("active") or {}

def dismiss(ws: Path | None = None) -> None:
    data = _load(ws)
    data["active"] = None
    _save(data, ws)

def status(ws: Path | None = None) -> dict | None:
    return _load(ws).get("active")

def blackboard(ws: Path | None = None) -> dict:
    p = paths.blackboard_path(ws)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"claims": []}

def add_claim(claim: str, evidence: list[str] | None = None, provenance: str = "", ws: Path | None = None) -> dict:
    bb = blackboard(ws)
    rec = {"claim": claim, "evidence": evidence or [], "provenance": provenance, "verdict": "unclassified", "ts": time.time()}
    bb.setdefault("claims", []).append(rec)
    paths.blackboard_path(ws).write_text(json.dumps(bb, indent=2), encoding="utf-8")
    return rec

def blackboard_read(ws=None):
    return blackboard(ws)

def blackboard_write(claim, evidence=None, provenance="", ws=None):
    return add_claim(claim, evidence=evidence, provenance=str(provenance), ws=ws)
