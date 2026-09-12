"""Pre-ingest privacy + financial gate.

Wraps curiosity-merge `find_gdpr_likely_pii` when available; otherwise uses a
stdlib regex fallback. Adds financial/pricing heuristics (severity warn).
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Callable

# --- optional curiosity-merge import -----------------------------------------

_CURIOSITY_PREFLIGHT = Path("/workspace/curiosity-merge/scripts/preflight.py")

_find_gdpr: Callable[[list[Path]], list[dict]] | None = None


def _load_curiosity_gdpr() -> Callable[[list[Path]], list[dict]] | None:
    global _find_gdpr
    if _find_gdpr is not None:
        return _find_gdpr
    path = Path(os_environ_curiosity())
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("okbay_curiosity_preflight", path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        # Avoid polluting sys.modules permanently on failure
        sys.modules["okbay_curiosity_preflight"] = mod
        spec.loader.exec_module(mod)
        fn = getattr(mod, "find_gdpr_likely_pii", None)
        if callable(fn):
            _find_gdpr = fn  # type: ignore[assignment]
            return _find_gdpr
    except Exception:
        sys.modules.pop("okbay_curiosity_preflight", None)
        return None
    return None


def os_environ_curiosity() -> str:
    import os
    return os.environ.get("OKBAY_CURIOSITY_PREFLIGHT", str(_CURIOSITY_PREFLIGHT))


# --- fallback PII regex (mirrors curiosity-merge core patterns) --------------

_EMAIL_RE = re.compile(
    r"(?<![\w.+-])"
    r"[^\s<>\"'\(\)\[\],;:@]+"
    r"@"
    r"[^\s<>\"'\(\)\[\],;:@]+"
    r"\.[^\s<>\"'\(\)\[\],;:@]{2,}"
)
_RESERVED_TEST_DOMAINS = (
    "example.com", "example.org", "example.net",
    "test.com", "test.local", "invalid", "localhost",
)
_PHONE_E164_RE = re.compile(r"(?<![\w+])\+\d(?:[\s\-]?\d){7,14}(?!\w)")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
_CC_RE = re.compile(
    r"\b(?:"
    r"4[\s\-]?(?:\d[\s\-]?){12,18}"
    r"|5[1-5][\s\-]?(?:\d[\s\-]?){12,17}"
    r"|3[47][\s\-]?(?:\d[\s\-]?){11,16}"
    r"|6(?:011|5\d{2})[\s\-]?(?:\d[\s\-]?){8,13}"
    r")\d\b"
)


def _is_test_email(addr: str) -> bool:
    domain = addr.rsplit("@", 1)[-1].lower().rstrip(".")
    for d in _RESERVED_TEST_DOMAINS:
        if domain == d or domain.endswith("." + d):
            return True
    tld = domain.rsplit(".", 1)[-1]
    return tld in {"test", "example", "invalid", "localhost", "local"}


def _digit_count(s: str) -> int:
    return sum(1 for c in s if c.isdigit())


def _fallback_gdpr(files: list[Path]) -> list[dict]:
    out: list[dict] = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hits: list[tuple[str, int, list[str]]] = []
        emails = [m.group(0) for m in _EMAIL_RE.finditer(text) if not _is_test_email(m.group(0))]
        if emails:
            hits.append(("email", len(emails), emails[:5]))
        phones = [m.group(0) for m in _PHONE_E164_RE.finditer(_EMAIL_RE.sub("", text))]
        if phones:
            hits.append(("phone", len(phones), phones[:5]))
        for kind, label, rx in (
            ("ssn", "US SSN", _SSN_RE),
            ("iban", "IBAN", _IBAN_RE),
        ):
            matched = [m.group(0) for m in rx.finditer(text)]
            if matched:
                hits.append((label, len(matched), matched[:5]))
        ccs = [m.group(0) for m in _CC_RE.finditer(text) if _digit_count(m.group(0)) >= 13]
        if ccs:
            hits.append(("payment-card-like", len(ccs), ccs[:5]))
        if not hits:
            continue
        summary = ", ".join(f"{c}×{label}" for label, c, _ in hits)
        samples = [f"{label}: {s}" for label, _, samples in hits for s in samples]
        out.append({
            "kind": "gdpr_likely_pii",
            "severity": "warn",
            "subject": str(p),
            "summary": f"possible personal data ({summary})",
            "rationale": "Fallback regex PII detector (curiosity-merge preflight unavailable).",
            "samples": samples,
        })
    return out


def find_gdpr_likely_pii(files: list[Path]) -> list[dict]:
    fn = _load_curiosity_gdpr()
    if fn is not None:
        try:
            return list(fn(files))
        except Exception:
            pass
    return _fallback_gdpr(files)


# --- financial / pricing heuristics ------------------------------------------

_CURRENCY_RE = re.compile(
    r"(?<!\w)(?:USD|EUR|GBP|CHF|CAD|AUD|JPY|\$|€|£|¥)\s?-?\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,4})?"
    r"|\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\s?(?:USD|EUR|GBP|CHF)\b",
    re.I,
)
_ACCOUNT_RE = re.compile(r"\b(?:account|acct|a/c)[\s#:.-]*\d{6,}\b", re.I)
_FINANCIAL_KEYWORDS = re.compile(
    r"\b(?:"
    r"invoice|pricing|price\s+list|unit\s+price|list\s+price|"
    r"ARR\b|MRR\b|burn\s+rate|runway\b|gross\s+margin|"
    r"bank\s+transfer|wire\s+transfer|routing\s+number|"
    r"salary|compensation|payroll|COGS|EBITDA|"
    r"quote\s+#|SOW\s+value|contract\s+value"
    r")\b",
    re.I,
)


def find_financial_signals(files: list[Path]) -> list[dict]:
    out: list[dict] = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        currencies = [m.group(0) for m in _CURRENCY_RE.finditer(text)]
        accounts = [m.group(0) for m in _ACCOUNT_RE.finditer(text)]
        keywords = [m.group(0) for m in _FINANCIAL_KEYWORDS.finditer(text)]
        if not (currencies or accounts or keywords):
            continue
        parts = []
        if currencies:
            parts.append(f"{len(currencies)}×currency")
        if accounts:
            parts.append(f"{len(accounts)}×account")
        if keywords:
            parts.append(f"{len(keywords)}×keyword")
        samples = (
            [f"currency: {c}" for c in currencies[:3]]
            + [f"account: {a}" for a in accounts[:3]]
            + [f"keyword: {k}" for k in keywords[:5]]
        )
        out.append({
            "kind": "financial_pricing",
            "severity": "warn",
            "subject": str(p),
            "summary": f"possible financial/pricing content ({', '.join(parts)})",
            "rationale": (
                "Heuristics for currency amounts, account numbers, and commercial "
                "pricing terms (invoice, ARR, burn rate, etc.). Confirm before "
                "copying into the shared vault."
            ),
            "samples": samples,
        })
    return out


def _safe_findings(findings: list[dict]) -> list[dict]:
    """Strip sample values for API responses that may be logged."""
    safe = []
    for f in findings:
        item = {k: v for k, v in f.items() if k != "samples"}
        item["sample_count"] = len(f.get("samples") or [])
        safe.append(item)
    return safe


def _needs_confirm(findings: list[dict]) -> bool:
    for f in findings:
        sev = str(f.get("severity") or "").lower()
        if sev in {"warn", "block", "error"}:
            return True
    return False


def scan_path(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return {"ok": False, "error": "not found", "path": str(p), "findings": [], "needs_confirm": False}
    if p.is_dir():
        files = [f for f in p.rglob("*") if f.is_file() and ".git" not in f.parts][:50]
    else:
        files = [p]
    # Skip huge/binary-looking files for text scans
    scanned: list[Path] = []
    for f in files:
        try:
            if f.stat().st_size > 2_000_000:
                continue
            head = f.read_bytes()[:1024]
            if b"\x00" in head:
                continue
        except OSError:
            continue
        scanned.append(f)
    findings = find_gdpr_likely_pii(scanned) + find_financial_signals(scanned)
    needs = _needs_confirm(findings)
    return {
        "ok": True,
        "path": str(p),
        "findings": _safe_findings(findings),
        "needs_confirm": needs,
        "finding_count": len(findings),
        "detector": "curiosity-merge" if _load_curiosity_gdpr() else "fallback-regex",
    }


def gate_ingest(path: str | Path, confirm: bool = False) -> dict[str, Any] | None:
    """Return a needs_confirm payload if blocked; None if ingest may proceed."""
    scan = scan_path(path)
    if scan.get("needs_confirm") and not confirm:
        return {
            "ok": False,
            "needs_confirm": True,
            "path": scan.get("path"),
            "findings": scan.get("findings") or [],
            "finding_count": scan.get("finding_count", 0),
            "message": "Privacy/financial signals found; re-run with confirm=True after UI approval.",
        }
    return None
