"""Standing desks: curate / work / code / deck."""
from __future__ import annotations
import json, time
from pathlib import Path
from . import paths
DESK_KINDS = ("curate", "work", "code", "deck")

def _load(ws=None):
    p = paths.desks_path(ws)
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError: pass
    return {"active": None, "history": []}

def _save(data, ws=None):
    p = paths.desks_path(ws)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def start(kind, objective="", ws=None):
    kind = kind.lower().strip()
    if kind not in DESK_KINDS:
        raise ValueError(kind)
    desk = {"id": kind, "state": "working", "objective": objective, "seated_at": time.time()}
    data = _load(ws); data["active"] = desk; data["history"].append(desk); _save(data, ws)
    return desk

def stop(kind=None, ws=None):
    data = _load(ws)
    if data.get("active"): data["active"]["state"] = "quiet"
    _save(data, ws)
    return data.get("active") or {}

def status(ws=None):
    return _load(ws).get("active")
