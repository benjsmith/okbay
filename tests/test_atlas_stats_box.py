"""The Atlas node/edge counts live only in the stats box over the graph."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "src" / "okbay" / "static" / "atlas.html"


def _html() -> str:
    return ATLAS.read_text(encoding="utf-8")


def test_sidebar_has_no_count_text():
    html = _html()
    assert "meta-counts" not in html
    sidebar = html[html.index('<aside id="sidebar"'):html.index("</aside>")]
    assert "nodes" not in sidebar and "links" not in sidebar


def test_stats_box_sits_in_graph_pane():
    html = _html()
    pane = html[html.index('<div id="graph-pane">'):html.index('<div id="graph"')]
    assert 'id="status"' in pane


def _extract(name: str, html: str) -> str:
    start = html.index(f"  function {name}(")
    end = html.index("\n  }\n", start) + 4
    return html[start:end]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_stats_box_shows_counts_and_returns_after_messages():
    html = _html()
    code = _extract("formatStats", html) + "\n" + _extract("setStatus", html)
    script = r"""
function el() {
  const cls = new Set();
  return { style: {}, textContent: '', children: [],
    classList: { add: (...a) => a.forEach(c => cls.add(c)), remove: (...a) => a.forEach(c => cls.delete(c)),
      toggle: (c, on) => on ? cls.add(c) : cls.delete(c), contains: c => cls.has(c) },
    appendChild(c) { this.children.push(c); this.textContent += c.textContent || ''; },
  };
}
const document = { createTextNode: t => ({ textContent: t }), createElement: () => ({ setAttribute() {}, textContent: '' }) };
const statusEl = el();
let statsText = '';
""" + code + r"""
const out = {};
setStatus('');
out.emptyHidden = statusEl.style.display;
statsText = formatStats(27905, 80486);
setStatus('');
out.stats = statusEl.textContent;
out.statsClass = statusEl.classList.contains('is-stats');
setStatus('Focused · entities/aaron-pottier');
out.toast = statusEl.textContent;
out.toastClass = statusEl.classList.contains('is-stats');
setStatus('');
out.back = statusEl.textContent;
console.log(JSON.stringify(out));
"""
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["emptyHidden"] == "none"
    assert out["stats"] == "27,905 nodes · 80,486 edges"
    assert out["statsClass"] is True
    assert out["toast"] == "Focused · entities/aaron-pottier"
    assert out["toastClass"] is False
    assert out["back"] == "27,905 nodes · 80,486 edges"


def test_scene_ready_updates_the_stats_box():
    html = _html()
    handler = html[html.index("ev.kind !== 'scene-ready'"):]
    handler = handler[:handler.index("});")]
    assert "statsText = formatStats(s.nodeCount, s.edgeCount)" in handler
    assert not re.search(r"setStatus\('scene-ready", html)
