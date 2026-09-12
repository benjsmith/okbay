"""Unit tests for work coverage, privacy gate, watcher helpers, code policy."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("OKBAY_WORKSPACE", str(Path("/tmp/okbay-wc-ws")))
os.environ.setdefault("XDG_STATE_HOME", str(Path("/tmp/okbay-wc-state")))
os.environ.setdefault("XDG_CONFIG_HOME", str(Path("/tmp/okbay-wc-config")))

from okbay import code_policy, ingest, paths, privacy_gate, watch, workroot, wiki  # noqa: E402


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    work = tmp_path / "home" / "Work"
    work.mkdir(parents=True)
    hub = work / "okbay"
    monkeypatch.setenv("OKBAY_WORKSPACE", str(hub))
    monkeypatch.setenv("OKBAY_WORK_ROOT", str(work))
    # Force fallback regex (still fine if curiosity-merge exists)
    root = paths.ensure_workspace(hub)
    return {"tmp": tmp_path, "work": work, "hub": root}


def test_opt_out_skips_ingest(env):
    work = env["work"]
    secret = work / "secrets"
    secret.mkdir()
    f = secret / "ssn.txt"
    f.write_text("plain note without pii markers\n")
    workroot.opt_out(secret)
    result = ingest.ingest_path(f)
    assert result.get("ok") is False
    assert result.get("reason") == "opt_out"


def test_opt_in_restores(env):
    work = env["work"]
    d = work / "maybe-private"
    d.mkdir()
    workroot.opt_out(d)
    assert workroot.is_opted_out(d)
    workroot.opt_in(d)
    assert not workroot.is_opted_out(d)


def test_pii_needs_confirm(env):
    f = env["hub"] / "drop-pii.txt"
    f.write_text("Contact alice@acme-corp.com and +12025550123 please.\n")
    scan = privacy_gate.scan_path(f)
    assert scan["needs_confirm"] is True
    blocked = ingest.ingest_path(f, confirm=False)
    assert blocked.get("ok") is False
    assert blocked.get("needs_confirm") is True
    assert not list(paths.vault(env["hub"]).glob("drop-pii*"))


def test_financial_needs_confirm(env):
    f = env["hub"] / "pricing.txt"
    f.write_text("Q3 invoice total USD 12,500.00 and ARR runway notes.\n")
    scan = privacy_gate.scan_path(f)
    assert scan["needs_confirm"] is True
    kinds = {x.get("kind") for x in scan["findings"]}
    assert "financial_pricing" in kinds


def test_confirm_allows_ingest(env):
    f = env["hub"] / "ok-to-ingest.txt"
    f.write_text("Price list USD 99.00 for the invoice.\n")
    blocked = ingest.ingest_path(f, confirm=False)
    assert blocked.get("needs_confirm") is True
    ok = ingest.ingest_path(f, confirm=True)
    assert ok.get("ok") is True
    assert Path(ok["vault"]).is_file()


def test_clean_ingest_no_confirm(env):
    f = env["hub"] / "clean.txt"
    f.write_text("The landlord requires two months deposit.\n")
    result = ingest.ingest_path(f)
    assert result.get("ok") is True


def test_git_dir_not_ingested(env):
    work = env["work"]
    repo = work / "myapp"
    repo.mkdir()
    (repo / ".git").mkdir()
    src = repo / "main.py"
    src.write_text("print('hello')\n")
    result = ingest.ingest_path(src)
    assert result.get("skipped_ingest") is True or result.get("reason") == "code_repo"
    assert result.get("kind") == "decision"
    # No vault copy of source
    assert not (paths.vault(env["hub"]) / "main.py").exists()
    page = wiki.get_page(result["stem"])
    assert page is not None
    assert page.kind == "decision"


def test_workspace_named(env):
    bio = env["work"] / "biocure"
    bio.mkdir()
    workroot.add_workspace("biocure", bio)
    listed = workroot.list_workspaces()
    assert "biocure" in listed["workspaces"]
    used = workroot.use_workspace("biocure")
    assert used["ok"] is True
    assert paths.workspace().resolve() == bio.resolve()
    assert (bio / "vault").is_dir()


def test_debounce_helper():
    pending = {"a": 100.0, "b": 101.0}
    ready = watch.debounce_ready(pending, now=103.0, delay=2.5)
    assert ready == ["a"]
    assert "a" not in pending and "b" in pending
    ready2 = watch.debounce_ready(pending, now=104.0, delay=2.5)
    assert ready2 == ["b"]
    assert pending == {}


def test_watch_once_skips_opt_out(env, monkeypatch):
    work = env["work"]
    docs = work / "docs"
    docs.mkdir()
    good = docs / "note.txt"
    good.write_text("A harmless meeting note about lunch.\n")
    bad_dir = work / "hr"
    bad_dir.mkdir()
    bad = bad_dir / "salaries.txt"
    bad.write_text("A harmless placeholder.\n")
    workroot.opt_out(bad_dir)
    # Seed mtime index empty so both appear as changed; opt-out must skip
    monkeypatch.setenv("OKBAY_WORK_ROOT", str(work))
    out = watch.watch_once(root=work, confirm=True, ws=env["hub"])
    assert out["ok"] is True
    paths_touched = []
    for r in out["results"]:
        paths_touched.append(r.get("path") or r.get("vault") or "")
        if r.get("reason") == "opt_out":
            assert "hr" in (r.get("path") or "")
    # Ensure salaries not vault-copied
    assert not (paths.vault(env["hub"]) / "salaries.txt").exists()


def test_changed_since_index(env, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(env["tmp"] / "state2"))
    f = env["work"] / "x.txt"
    f.write_text("one\n")
    c1 = watch.changed_since_index([f])
    assert f in c1
    c2 = watch.changed_since_index([f])
    assert c2 == []
    time.sleep(0.05)
    f.write_text("two\n")
    c3 = watch.changed_since_index([f])
    assert f in c3


def test_coverage_status(env):
    st = workroot.coverage_status()
    assert Path(st["work_root"]) == env["work"].resolve()
    assert "config" in st


def test_code_policy_git_root(env):
    repo = env["work"] / "lib"
    (repo / ".git").mkdir(parents=True)
    nested = repo / "src" / "a.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("x=1\n")
    assert code_policy.git_root(nested) == repo.resolve()
    assert code_policy.should_skip_code_ingest(nested, ws=env["hub"])
