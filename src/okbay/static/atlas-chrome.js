/* Slice 2+ — Okbay atlas chrome: Fuse sidebar, wiki modal, labels/edges, ingest,
 * workspace switcher, minimap toggle, viewer toggle, keybindings, help.
 * CE cues from wiki-view sidebar.js / modal.js / atlas.js initAtlasControls.
 */
(function (global) {
  'use strict';

  var TYPE_CANONICAL = {
    analysis: 'analysis', analyses: 'analysis',
    concept: 'concept', concepts: 'concept',
    entity: 'entity', entities: 'entity',
    evidence: 'evidence',
    fact: 'fact', facts: 'fact',
    figure: 'figure', figures: 'figure',
    table: 'table', tables: 'table',
    'extracted-table': 'table', 'summary-table': 'table',
    source: 'source', sources: 'source',
    note: 'note', notes: 'note',
    todo: 'todo-list', 'todo-list': 'todo-list',
    project: 'project', projects: 'project',
    unclassified: 'unclassified', hub: 'hub', missing: 'missing'
  };
  var TYPE_ORDER = [
    'project', 'analysis', 'concept', 'entity', 'evidence', 'fact', 'figure',
    'table', 'source', 'note', 'todo-list', 'hub', 'unclassified', 'missing'
  ];
  var TYPE_LABEL = {
    project: 'Projects', analysis: 'Analyses', concept: 'Concepts',
    entity: 'Entities', evidence: 'Evidence', fact: 'Facts', figure: 'Figures',
    table: 'Tables', source: 'Sources', note: 'Notes', 'todo-list': 'Todos',
    hub: 'Hubs', unclassified: 'Unclassified', missing: 'Missing'
  };
  var LABEL_DEFAULTS = ['concept', 'entity', 'note', 'todo-list'];
  var LABEL_TYPES_KEY = 'okbay.label-types';
  var LABEL_MODE_KEY = 'okbay.label-mode';
  var EDGE_MODE_KEY = 'okbay.edge-mode';
  var VIEWER_KEY = 'okbay.viewer';
  var MINIMAP_KEY = 'okbay.minimap';

  function canonicalType(t) {
    var key = String(t || '').toLowerCase();
    return TYPE_CANONICAL[key] || key || 'unclassified';
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c];
    });
  }
  function escapeAttr(s) { return escapeHtml(s); }

  function applyPalette(palette) {
    if (!palette || typeof palette !== 'object') return;
    Object.keys(palette).forEach(function (k) {
      var v = palette[k];
      if (!v || typeof v !== 'string') return;
      try {
        document.documentElement.style.setProperty('--dot-' + k, v);
      } catch (e) {}
    });
  }

  function propsBlob(node, page) {
    var props = (page && page.properties) || {};
    var bits = [];
    var sources = props.sources || node.sources || [];
    if (Array.isArray(sources)) bits.push(sources.join(' '));
    else if (sources) bits.push(String(sources));
    Object.keys(props).forEach(function (k) {
      if (k === 'sources' || k === 'files') return;
      var v = props[k];
      bits.push(Array.isArray(v) ? v.join(' ') : String(v));
    });
    return bits.join(' ');
  }

  /* ── Sidebar ───────────────────────────────────────────────────── */
  var Sidebar = {
    listEl: null,
    searchEl: null,
    fuse: null,
    records: [],
    collapsed: new Set(),
    onSelect: null,
    palette: {},

    init: function (data, opts) {
      opts = opts || {};
      this.listEl = document.getElementById('sidebar-list');
      this.searchEl = document.getElementById('sidebar-search');
      this.onSelect = opts.onSelect || null;
      this.onHighlight = opts.onHighlight || null;
      this.palette = data.palette || {};
      applyPalette(this.palette);
      var pages = data.pages || {};
      this.records = (data.nodes || []).map(function (n) {
        var page = pages[n.id] || {};
        return {
          id: n.id,
          title: n.title || n.id,
          type: n.type || 'note',
          props: propsBlob(n, page)
        };
      });
      if (typeof Fuse === 'undefined') {
        console.warn('Fuse.js missing — search falls back to includes');
        this.fuse = null;
      } else {
        this.fuse = new Fuse(this.records, {
          keys: [
            { name: 'title', weight: 0.7 },
            { name: 'type', weight: 0.1 },
            { name: 'props', weight: 0.2 }
          ],
          threshold: 0.35,
          ignoreLocation: true,
          minMatchCharLength: 1
        });
      }
      try {
        var stored = JSON.parse(localStorage.getItem('okbay.collapsed-types') || '[]');
        this.collapsed = new Set(stored);
      } catch (e) { this.collapsed = new Set(); }

      this.renderGrouped();
      var self = this;
      function emitHighlight(items) {
        if (typeof self.onHighlight !== 'function') return;
        var ids = (items || []).map(function (r) { return r.id; }).slice(0, 80);
        self.onHighlight(ids);
      }
      this.searchEl.addEventListener('input', function (ev) {
        var q = ev.target.value.trim();
        if (!q) {
          self.renderGrouped();
          emitHighlight([]);
          return;
        }
        var hits;
        if (self.fuse) {
          hits = self.fuse.search(q, { limit: 200 }).map(function (r) { return r.item; });
        } else {
          var needle = q.toLowerCase();
          hits = self.records.filter(function (r) {
            return (r.title + ' ' + r.type + ' ' + r.props).toLowerCase().indexOf(needle) >= 0;
          }).slice(0, 200);
        }
        self.renderFlat(hits);
        emitHighlight(hits);
      });
      // Expand/collapse-all (CE sidebar-toggle-all): if any group expanded → collapse all; else expand all.
      var toggleAllBtn = document.getElementById('sidebar-toggle-all');
      if (toggleAllBtn) {
        toggleAllBtn.addEventListener('click', function (ev) {
          ev.preventDefault();
          self.toggleAllGroups();
        });
      }
      this.listEl.addEventListener('click', function (ev) {
        var allBtn = ev.target.closest && ev.target.closest('[data-action="toggle-all-groups"]');
        if (allBtn) {
          self.toggleAllGroups();
          return;
        }
        var header = ev.target.closest && ev.target.closest('[data-action="toggle-group"]');
        if (header) {
          var t = header.dataset.type;
          if (self.collapsed.has(t)) self.collapsed.delete(t); else self.collapsed.add(t);
          try {
            localStorage.setItem('okbay.collapsed-types', JSON.stringify(Array.from(self.collapsed)));
          } catch (e) {}
          var group = header.closest('.type-group');
          if (group) group.dataset.collapsed = self.collapsed.has(t) ? 'true' : 'false';
          return;
        }
        var row = ev.target.closest && ev.target.closest('.sidebar-row');
        if (!row) return;
        var id = row.dataset.id;
        // Selecting a hit also focuses that node on the graph (even mid-search).
        if (typeof self.onHighlight === 'function') self.onHighlight([id]);
        if (typeof self.onSelect === 'function') self.onSelect(id);
      });
    },

    toggleAllGroups: function () {
      var types = [];
      var seen = new Set();
      this.records.forEach(function (r) {
        var t = canonicalType(r.type);
        if (!seen.has(t)) { seen.add(t); types.push(t); }
      });
      if (!types.length) return;
      var anyExpanded = types.some(function (t) { return !this.collapsed.has(t); }, this);
      this.collapsed = anyExpanded ? new Set(types) : new Set();
      try {
        localStorage.setItem('okbay.collapsed-types', JSON.stringify(Array.from(this.collapsed)));
      } catch (e) {}
      if (!this.searchEl || !this.searchEl.value.trim()) this.renderGrouped();
    },

    rowHtml: function (rec) {
      var t = canonicalType(rec.type);
      var color = (Sidebar.palette && Sidebar.palette[t]) || '';
      var style = color ? ' style="background:' + escapeAttr(color) + '"' : '';
      return '<button class="sidebar-row" data-id="' + escapeAttr(rec.id) + '" role="option">' +
        '<span class="dot" data-type="' + escapeAttr(t) + '"' + style + '></span>' +
        '<span class="row-title">' + escapeHtml(rec.title) + '</span>' +
        '</button>';
    },

    renderGrouped: function () {
      var byType = new Map();
      this.records.forEach(function (rec) {
        var t = canonicalType(rec.type);
        if (!byType.has(t)) byType.set(t, []);
        byType.get(t).push(rec);
      });
      var seen = new Set();
      var ordered = [];
      TYPE_ORDER.forEach(function (t) {
        if (byType.has(t) && !seen.has(t)) { ordered.push(t); seen.add(t); }
      });
      Array.from(byType.keys()).sort().forEach(function (t) {
        if (!seen.has(t)) ordered.push(t);
      });
      var self = this;
      var html = ordered.map(function (t) {
        var recs = byType.get(t).slice().sort(function (a, b) {
          return a.title.localeCompare(b.title, undefined, { sensitivity: 'base' });
        });
        var isCollapsed = self.collapsed.has(t);
        var label = TYPE_LABEL[t] || (t.charAt(0).toUpperCase() + t.slice(1));
        var color = (self.palette && self.palette[t]) || '';
        var style = color ? ' style="background:' + escapeAttr(color) + '"' : '';
        return '<section class="type-group" data-type="' + escapeAttr(t) +
          '" data-collapsed="' + (isCollapsed ? 'true' : 'false') + '">' +
          '<button class="type-group-header" data-action="toggle-group" data-type="' +
          escapeAttr(t) + '">' +
          '<span class="group-chev">▸</span>' +
          '<span class="dot" data-type="' + escapeAttr(t) + '"' + style + '></span>' +
          '<span class="type-group-name">' + escapeHtml(label) + '</span>' +
          '<span class="type-group-count">' + recs.length + '</span>' +
          '</button>' +
          '<div class="type-group-body">' + recs.map(self.rowHtml.bind(self)).join('') + '</div>' +
          '</section>';
      }).join('');
      this.listEl.innerHTML = html || '<div class="sidebar-empty">No pages</div>';
    },

    renderFlat: function (items) {
      if (!items.length) {
        this.listEl.innerHTML = '<div class="sidebar-empty">No matches</div>';
        return;
      }
      this.listEl.innerHTML = items.map(this.rowHtml.bind(this)).join('');
    },

    setActive: function (pageId) {
      this.listEl.querySelectorAll('.sidebar-row').forEach(function (row) {
        row.dataset.active = (row.dataset.id === pageId) ? 'true' : '';
      });
      var active = this.listEl.querySelector('.sidebar-row[data-active="true"]');
      if (active && active.scrollIntoView) active.scrollIntoView({ block: 'nearest' });
    },

    focusSearch: function (selectAll) {
      if (!this.searchEl) return;
      this.searchEl.focus();
      if (selectAll !== false && this.searchEl.value) {
        try { this.searchEl.select(); } catch (e) {}
      }
    },

    blurSearch: function (clear) {
      if (!this.searchEl) return;
      if (clear) {
        this.searchEl.value = '';
        this.renderGrouped();
        if (typeof this.onHighlight === 'function') this.onHighlight([]);
      }
      this.searchEl.blur();
    },

    collapseAllGroups: function () {
      var types = [];
      var seen = new Set();
      this.records.forEach(function (r) {
        var t = canonicalType(r.type);
        if (!seen.has(t)) { seen.add(t); types.push(t); }
      });
      this.collapsed = new Set(types);
      try {
        localStorage.setItem('okbay.collapsed-types', JSON.stringify(Array.from(this.collapsed)));
      } catch (e) {}
      if (!this.searchEl || !this.searchEl.value.trim()) this.renderGrouped();
    },

    expandAllGroups: function () {
      this.collapsed = new Set();
      try {
        localStorage.setItem('okbay.collapsed-types', JSON.stringify([]));
      } catch (e) {}
      if (!this.searchEl || !this.searchEl.value.trim()) this.renderGrouped();
    }
  };

  /* ── Label / type / edge controls (CE initAtlasControls slim port) ─ */
  var Controls = {
    handle: null,
    mode: 'auto',
    edgeMode: 'auto',
    types: null,
    onViewerToggle: null,
    onToast: null,

    readTypes: function () {
      try {
        var saved = JSON.parse(localStorage.getItem(LABEL_TYPES_KEY) || 'null');
        if (Array.isArray(saved)) return new Set(saved.map(canonicalType));
      } catch (e) {}
      return new Set(LABEL_DEFAULTS);
    },

    init: function (handle, opts) {
      opts = opts || {};
      this.handle = handle;
      this.types = this.readTypes();
      this.onViewerToggle = opts.onViewerToggle || null;
      this.onToast = opts.onToast || null;
      try {
        var m = localStorage.getItem(LABEL_MODE_KEY);
        if (m === 'auto' || m === 'on' || m === 'off') this.mode = m;
      } catch (e) {}
      try {
        var em = localStorage.getItem(EDGE_MODE_KEY);
        if (em === 'auto' || em === 'on' || em === 'off') this.edgeMode = em;
      } catch (e) {}
      var modeButton = document.getElementById('label-mode');
      var modeState = document.getElementById('label-mode-state');
      var edgeButton = document.getElementById('edge-mode');
      var edgeState = document.getElementById('edge-mode-state');
      var typeButton = document.getElementById('label-types');
      var typeState = document.getElementById('label-types-state');
      var typePanel = document.getElementById('label-types-panel');
      var viewerButton = document.getElementById('viewer-mode');
      var self = this;

      function paintLabels() {
        if (modeState) modeState.textContent = self.mode;
        if (typeState) typeState.textContent = self.types.size + '/12';
        document.documentElement.dataset.labels = self.mode;
        if (self.handle && typeof self.handle.setLabels === 'function') {
          self.handle.setLabels(self.mode, Array.from(self.types));
        }
      }
      function paintEdges() {
        if (edgeState) edgeState.textContent = self.edgeMode;
        document.documentElement.dataset.edges = self.edgeMode;
        if (self.handle && typeof self.handle.setEdges === 'function') {
          self.handle.setEdges(self.edgeMode);
        }
      }
      function paint() {
        paintLabels();
        paintEdges();
      }
      this.paint = paint;
      this.paintLabels = paintLabels;
      this.paintEdges = paintEdges;

      if (modeButton) {
        modeButton.addEventListener('click', function () { self.cycleMode(); });
      }
      if (edgeButton) {
        edgeButton.classList.remove('hidden');
        edgeButton.hidden = false;
        edgeButton.addEventListener('click', function () { self.cycleEdgeMode(); });
      }
      if (viewerButton) {
        viewerButton.classList.remove('hidden');
        viewerButton.hidden = false;
        viewerButton.addEventListener('click', function (ev) {
          ev.stopPropagation();
          if (window.OkbayAtlasChrome && OkbayAtlasChrome.Views && typeof OkbayAtlasChrome.Views.togglePanel === 'function') {
            OkbayAtlasChrome.Views.togglePanel();
          } else if (typeof self.onViewerToggle === 'function') {
            self.onViewerToggle();
          }
        });
      }

      if (typePanel && typeButton) {
        typePanel.querySelectorAll('.label-types-row').forEach(function (row) {
          var key = canonicalType(row.dataset.type);
          row.dataset.type = key;
          var input = row.querySelector('input[type=checkbox]');
          if (!input) return;
          input.checked = self.types.has(key);
          input.addEventListener('change', function () {
            if (input.checked) self.types.add(key); else self.types.delete(key);
            try {
              localStorage.setItem(LABEL_TYPES_KEY, JSON.stringify(Array.from(self.types)));
            } catch (e) {}
            paintLabels();
          });
        });
        typeButton.addEventListener('click', function (ev) {
          ev.stopPropagation();
          typePanel.classList.toggle('hidden');
        });
        var typeReset = document.getElementById('label-types-reset');
        if (typeReset) {
          typeReset.addEventListener('click', function () {
            self.types = new Set(LABEL_DEFAULTS);
            typePanel.querySelectorAll('.label-types-row').forEach(function (row) {
              var input = row.querySelector('input[type=checkbox]');
              if (input) input.checked = self.types.has(row.dataset.type);
            });
            try {
              localStorage.setItem(LABEL_TYPES_KEY, JSON.stringify(Array.from(self.types)));
            } catch (e) {}
            paintLabels();
          });
        }
        document.addEventListener('click', function (ev) {
          if (!typePanel.classList.contains('hidden') &&
              !typePanel.contains(ev.target) &&
              ev.target !== typeButton && !typeButton.contains(ev.target)) {
            typePanel.classList.add('hidden');
          }
        });
      }
      paint();
      return this;
    },

    cycleMode: function () {
      var order = ['auto', 'on', 'off'];
      this.mode = order[(order.indexOf(this.mode) + 1) % order.length];
      try { localStorage.setItem(LABEL_MODE_KEY, this.mode); } catch (e) {}
      if (typeof this.paintLabels === 'function') this.paintLabels();
      else if (typeof this.paint === 'function') this.paint();
      return this.mode;
    },

    cycleEdgeMode: function () {
      var order = ['auto', 'on', 'off'];
      this.edgeMode = order[(order.indexOf(this.edgeMode) + 1) % order.length];
      try { localStorage.setItem(EDGE_MODE_KEY, this.edgeMode); } catch (e) {}
      if (typeof this.paintEdges === 'function') this.paintEdges();
      else if (typeof this.paint === 'function') this.paint();
      if (typeof this.onToast === 'function') this.onToast('edges:' + this.edgeMode);
      return this.edgeMode;
    },

    setViewerState: function (mode) {
      var state = document.getElementById('viewer-mode-state');
      var btn = document.getElementById('viewer-mode');
      if (state) state.textContent = mode;
      if (btn) {
        btn.title = 'Switch view (v)';
        btn.classList.remove('hidden');
        btn.hidden = false;
      }
      document.documentElement.dataset.viewer = mode;
      document.documentElement.dataset.view = mode;
    },

    isTypesPanelOpen: function () {
      var typePanel = document.getElementById('label-types-panel');
      return !!(typePanel && !typePanel.classList.contains('hidden'));
    },

    closeTypesPanel: function () {
      var typePanel = document.getElementById('label-types-panel');
      if (typePanel) typePanel.classList.add('hidden');
    },

    toggleTypesPanel: function () {
      var typePanel = document.getElementById('label-types-panel');
      if (!typePanel) return false;
      typePanel.classList.toggle('hidden');
      return !typePanel.classList.contains('hidden');
    },

    toggleMinimap: function () {
      var mm = document.querySelector('canvas.atlas-minimap');
      if (!mm) return null;
      mm.hidden = !mm.hidden;
      try { localStorage.setItem(MINIMAP_KEY, mm.hidden ? 'off' : 'on'); } catch (e) {}
      document.documentElement.dataset.atlasMinimap = mm.hidden ? 'hidden' : 'visible';
      return !mm.hidden;
    },

    applyMinimapPref: function () {
      var mm = document.querySelector('canvas.atlas-minimap');
      if (!mm) return;
      try {
        if (localStorage.getItem(MINIMAP_KEY) === 'off') mm.hidden = true;
      } catch (e) {}
      document.documentElement.dataset.atlasMinimap = mm.hidden ? 'hidden' : 'visible';
    }
  };

  /* ── Ingest (+) ─────────────────────────────────────────────────── */
  var Ingest = {
    api: '',
    onToast: null,
    init: function (opts) {
      opts = opts || {};
      this.api = opts.api || location.origin;
      this.onToast = opts.onToast || null;
      var btn = document.getElementById('ingest-add');
      var self = this;
      if (btn) btn.addEventListener('click', function () { self.promptAndIngest(); });
    },
    promptAndIngest: function () {
      var path = window.prompt('Ingest file or folder path (absolute or ~):', '');
      if (path == null) return;
      path = String(path).trim();
      if (!path) return;
      this.ingest(path, false);
    },
    ingest: function (path, confirm) {
      var self = this;
      var body = { path: path };
      if (confirm) body.confirm = true;
      return fetch(this.api + '/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      }).then(function (r) { return r.json(); }).then(function (doc) {
        if (doc && doc.needs_confirm) {
          var ok = window.confirm((doc.reason || 'Privacy gate') + '\n\nConfirm ingest anyway?');
          if (ok) return self.ingest(path, true);
          if (typeof self.onToast === 'function') self.onToast('ingest cancelled');
          return doc;
        }
        if (doc && doc.ok) {
          if (typeof self.onToast === 'function') {
            self.onToast('ingested · ' + (doc.stem || path));
          }
        } else if (typeof self.onToast === 'function') {
          self.onToast('ingest failed · ' + ((doc && (doc.error || doc.reason)) || 'unknown'));
        }
        return doc;
      }).catch(function (e) {
        if (typeof self.onToast === 'function') self.onToast('ingest error · ' + e);
      });
    }
  };

  /* ── Workspace switcher ─────────────────────────────────────────── */
  var Workspace = {
    api: '',
    onToast: null,
    onSwitched: null,
    init: function (opts) {
      opts = opts || {};
      this.api = opts.api || location.origin;
      this.onToast = opts.onToast || null;
      this.onSwitched = opts.onSwitched || null;
      var btn = document.getElementById('workspace-switch');
      var panel = document.getElementById('workspace-panel');
      var addBtn = document.getElementById('workspace-add');
      var splitBtn = document.getElementById('workspace-split');
      var self = this;
      if (btn) btn.addEventListener('click', function (ev) {
        ev.stopPropagation();
        self.toggle();
      });
      if (addBtn) addBtn.addEventListener('click', function () { self.promptAdd(); });
      if (splitBtn) splitBtn.addEventListener('click', function () { self.promptSplit(); });
      document.addEventListener('click', function (ev) {
        if (!panel || panel.classList.contains('hidden')) return;
        if (panel.contains(ev.target) || (btn && (ev.target === btn || btn.contains(ev.target)))) return;
        panel.classList.add('hidden');
      });
      this.refreshChip();
    },
    isOpen: function () {
      var panel = document.getElementById('workspace-panel');
      return !!(panel && !panel.classList.contains('hidden'));
    },
    close: function () {
      var panel = document.getElementById('workspace-panel');
      if (panel) panel.classList.add('hidden');
    },
    toggle: function () {
      var panel = document.getElementById('workspace-panel');
      if (!panel) return;
      if (panel.classList.contains('hidden')) {
        this.open();
      } else {
        panel.classList.add('hidden');
      }
    },
    open: function () {
      var panel = document.getElementById('workspace-panel');
      if (!panel) return;
      panel.classList.remove('hidden');
      this.refresh();
    },
    refreshChip: function () {
      var chip = document.getElementById('workspace-chip');
      var self = this;
      fetch(this.api + '/api/workspace/list')
        .then(function (r) { return r.json(); })
        .then(function (doc) {
          var name = doc.active || '';
          if (!name && doc.workspaces) {
            var cur = doc.current || '';
            Object.keys(doc.workspaces).forEach(function (k) {
              if (String(doc.workspaces[k]) === cur) name = k;
            });
          }
          if (chip) chip.textContent = name || 'workspace';
          document.documentElement.dataset.workspace = name || '';
        }).catch(function () {});
    },
    refresh: function () {
      var list = document.getElementById('workspace-list');
      var self = this;
      if (!list) return;
      list.innerHTML = '<div class="sidebar-empty">Loading…</div>';
      fetch(this.api + '/api/workspace/list')
        .then(function (r) { return r.json(); })
        .then(function (doc) {
          var named = doc.workspaces || {};
          var active = doc.active || '';
          var keys = Object.keys(named).sort();
          if (!keys.length) {
            list.innerHTML = '<div class="sidebar-empty">No workspaces</div>';
            return;
          }
          list.innerHTML = '';
          keys.forEach(function (name) {
            var row = document.createElement('button');
            row.type = 'button';
            row.className = 'workspace-row';
            row.dataset.name = name;
            if (name === active) row.dataset.active = 'true';
            row.innerHTML = '<span class="ws-name">' + escapeHtml(name) + '</span>' +
              '<span class="ws-path">' + escapeHtml(named[name]) + '</span>';
            row.addEventListener('click', function () { self.use(name); });
            list.appendChild(row);
          });
          self.refreshChip();
        }).catch(function (e) {
          list.innerHTML = '<div class="sidebar-empty">Failed: ' + escapeHtml(String(e)) + '</div>';
        });
    },
    use: function (name) {
      var self = this;
      return fetch(this.api + '/api/workspace/use', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name })
      }).then(function (r) { return r.json(); }).then(function (doc) {
        if (doc && doc.ok) {
          if (typeof self.onToast === 'function') self.onToast('workspace · ' + name);
          self.close();
          if (typeof self.onSwitched === 'function') self.onSwitched(doc);
          else window.location.reload();
        } else if (typeof self.onToast === 'function') {
          self.onToast('workspace failed · ' + ((doc && doc.error) || name));
        }
        return doc;
      });
    },
    promptAdd: function () {
      var name = window.prompt('Workspace name (e.g. biocure):', '');
      if (!name) return;
      var path = window.prompt('Workspace path (vault/wiki hub):', '');
      if (!path) return;
      var self = this;
      fetch(this.api + '/api/workspace/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), path: path.trim() })
      }).then(function (r) { return r.json(); }).then(function (doc) {
        if (doc && doc.ok) {
          if (typeof self.onToast === 'function') self.onToast('added · ' + name);
          self.refresh();
        } else if (typeof self.onToast === 'function') {
          self.onToast('add failed · ' + ((doc && doc.error) || ''));
        }
      });
    },
    promptSplit: function () {
      var name = window.prompt('Focused workspace name:', '');
      if (!name) return;
      var paths = window.prompt('Work subfolder path(s), comma-separated:', '');
      if (!paths) return;
      var self = this;
      var list = paths.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
      fetch(this.api + '/api/workspace/split', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), paths: list })
      }).then(function (r) { return r.json(); }).then(function (doc) {
        if (doc && doc.ok) {
          if (typeof self.onToast === 'function') self.onToast('split · ' + name);
          self.refresh();
        } else if (typeof self.onToast === 'function') {
          self.onToast('split failed · ' + ((doc && doc.error) || ''));
        }
      });
    }
  };

  /* ── Help overlay ───────────────────────────────────────────────── */
  var Help = {
    init: function () {
      var btn = document.getElementById('atlas-help-btn');
      var panel = document.getElementById('atlas-help');
      var close = document.getElementById('atlas-help-close');
      var self = this;
      if (btn) btn.addEventListener('click', function () { self.toggle(); });
      if (close) close.addEventListener('click', function () { self.close(); });
      if (panel) panel.addEventListener('click', function (ev) {
        if (ev.target === panel) self.close();
      });
    },
    isOpen: function () {
      var panel = document.getElementById('atlas-help');
      return !!(panel && !panel.classList.contains('hidden'));
    },
    open: function () {
      var panel = document.getElementById('atlas-help');
      if (panel) panel.classList.remove('hidden');
    },
    close: function () {
      var panel = document.getElementById('atlas-help');
      if (panel) panel.classList.add('hidden');
    },
    toggle: function () {
      if (this.isOpen()) this.close(); else this.open();
    }
  };

  /* ── Modal ─────────────────────────────────────────────────────── */
  var Modal = {
    api: '',
    pages: {},
    el: null,
    backdrop: null,
    titleEl: null,
    metaEl: null,
    propsEl: null,
    bodyEl: null,
    sourcesEl: null,
    locateEl: null,
    revealBtn: null,
    onNavigate: null,
    onClose: null,
    onLocate: null,
    currentId: null,
    lastDoc: null,

    init: function (data, opts) {
      opts = opts || {};
      this.api = opts.api || location.origin;
      this.pages = data.pages || {};
      this.onNavigate = opts.onNavigate || null;
      this.onClose = opts.onClose || null;
      this.onLocate = opts.onLocate || null;
      this.el = document.getElementById('modal');
      this.backdrop = document.getElementById('modal-backdrop');
      this.titleEl = document.getElementById('modal-title');
      this.metaEl = document.getElementById('modal-meta');
      this.propsEl = document.getElementById('modal-properties');
      this.bodyEl = document.getElementById('modal-body');
      this.sourcesEl = document.getElementById('modal-sources');
      this.locateEl = document.getElementById('modal-locate-status');
      this.revealBtn = document.getElementById('modal-reveal');
      var closeBtn = document.getElementById('modal-close');
      var self = this;
      this.backdrop.addEventListener('click', function () { self.close(); });
      if (closeBtn) closeBtn.addEventListener('click', function () { self.close(); });
      if (this.revealBtn) {
        this.revealBtn.addEventListener('click', function () {
          if (self.currentId) self.revealFiles(self.currentId, true);
        });
      }
      document.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape' && document.body.dataset.modal === 'open') self.close();
      });
      this.bodyEl.addEventListener('click', function (ev) {
        var a = ev.target.closest && ev.target.closest('a.wikilink');
        if (!a) return;
        ev.preventDefault();
        var target = a.dataset.page;
        if (target && typeof self.onNavigate === 'function') self.onNavigate(target);
      });
    },

    setLocateStatus: function (msg, isError) {
      if (!this.locateEl) return;
      if (!msg) {
        this.locateEl.classList.add('hidden');
        this.locateEl.textContent = '';
        return;
      }
      this.locateEl.classList.remove('hidden');
      this.locateEl.classList.toggle('error', !!isError);
      this.locateEl.textContent = msg;
    },

    revealFiles: function (pageId, doReveal) {
      var self = this;
      var url = this.api + '/api/locate?stem=' + encodeURIComponent(pageId) +
        '&reveal=' + (doReveal ? '1' : '0');
      this.setLocateStatus(doReveal ? 'Revealing…' : 'Resolving paths…');
      return fetch(url)
        .then(function (res) { return res.json(); })
        .then(function (doc) {
          if (self.currentId !== pageId) return doc;
          if (!doc || !doc.ok) {
            self.setLocateStatus((doc && doc.error) || 'Locate failed', true);
            return doc;
          }
          var bits = [];
          if (doc.wiki) bits.push('wiki: ' + doc.wiki);
          var files = doc.files || [];
          var sources = doc.sources || [];
          if (files.length) bits.push('files: ' + files.join(', '));
          else if (sources.length) bits.push('sources: ' + sources.join(', '));
          if (doc.reveal_via) bits.push('via ' + doc.reveal_via);
          if (doc.revealed) bits.push('opened ' + (Array.isArray(doc.revealed) ? doc.revealed.join(' ') : doc.revealed));
          if (doc.reveal_error) bits.push('reveal failed: ' + doc.reveal_error);
          var msg = bits.join(' · ') || 'Located';
          // Explicit Reveal click: surface launch failures in error styling.
          var err = !!(doc.reveal_error && doReveal);
          self.setLocateStatus(msg, err);
          if (typeof self.onLocate === 'function') self.onLocate(doc);
          return doc;
        })
        .catch(function (e) {
          if (self.currentId !== pageId) return;
          self.setLocateStatus('Locate error: ' + (e && e.message ? e.message : e), true);
        });
    },

    open: function (pageId) {
      var self = this;
      this.currentId = pageId;
      var stub = this.pages[pageId] || { id: pageId, title: pageId, type: 'note', properties: {}, path: '', sources: [], files: [] };
      this.titleEl.textContent = stub.title || pageId;
      this.metaEl.textContent = (stub.type || '') + (stub.path ? ' · ' + stub.path : '');
      this.renderProperties(stub);
      this.renderSources(
        (stub.properties && stub.properties.sources) || stub.sources,
        (stub.properties && stub.properties.files) || stub.files
      );
      this.bodyEl.innerHTML = '<p class="modal-loading">Loading…</p>';
      this.setLocateStatus('');
      this.show();
      // Resolve-only on open (no xdg-open spam); button reveals.
      this.revealFiles(pageId, false);
      fetch(this.api + '/api/atlas/page?stem=' + encodeURIComponent(pageId))
        .then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          return res.json();
        })
        .then(function (doc) {
          if (self.currentId !== pageId) return;
          self.lastDoc = doc;
          self.titleEl.textContent = doc.title || pageId;
          self.metaEl.textContent =
            (doc.type || doc.kind || '') + (doc.path ? ' · ' + doc.path : '');
          self.renderProperties(doc);
          self.renderSources(
            (doc.properties && doc.properties.sources) || doc.sources,
            (doc.properties && doc.properties.files) || doc.files
          );
          if (doc.body_html) {
            self.bodyEl.innerHTML = doc.body_html;
          } else if (doc.markdown) {
            self.bodyEl.innerHTML = '<pre class="md-raw">' + escapeHtml(doc.markdown) + '</pre>';
          } else {
            self.bodyEl.innerHTML = '<p class="modal-empty">No body</p>';
          }
        })
        .catch(function () {
          if (self.currentId !== pageId) return;
          self.bodyEl.innerHTML =
            '<p class="modal-empty">Page body unavailable (metadata only).</p>';
        });
      return true;
    },

    show: function () {
      this.el.classList.remove('hidden');
      this.backdrop.classList.remove('hidden');
      this.el.setAttribute('aria-hidden', 'false');
      this.backdrop.setAttribute('aria-hidden', 'false');
      document.body.dataset.modal = 'open';
      var scroll = this.el.querySelector('.modal-scroll');
      if (scroll) scroll.scrollTop = 0;
    },

    close: function () {
      this.el.classList.add('hidden');
      this.backdrop.classList.add('hidden');
      this.el.setAttribute('aria-hidden', 'true');
      this.backdrop.setAttribute('aria-hidden', 'true');
      document.body.dataset.modal = '';
      this.currentId = null;
      this.setLocateStatus('');
      if (location.hash.indexOf('#page=') === 0) {
        history.replaceState(null, '', location.pathname + location.search);
      }
      if (typeof this.onClose === 'function') this.onClose();
    },

    renderProperties: function (page) {
      var props = page.properties || {};
      var rows = [];
      rows.push(this.propRow('type', page.type || page.kind || '—'));
      if (page.path) rows.push(this.propRow('path', page.path));
      var order = ['created', 'updated'];
      var seen = { type: 1, path: 1, sources: 1, files: 1 };
      order.forEach(function (key) {
        if (key in props) {
          rows.push(Modal.propRow(key, props[key]));
          seen[key] = 1;
        }
      });
      Object.keys(props).forEach(function (k) {
        if (seen[k] || k === 'sources' || k === 'files') return;
        rows.push(Modal.propRow(k, props[k]));
      });
      this.propsEl.innerHTML = rows.join('') || '';
    },

    propRow: function (key, value) {
      var v;
      if (value == null || value === '') v = '<span class="faint">—</span>';
      else if (Array.isArray(value)) {
        v = value.map(function (item) {
          return '<div>' + escapeHtml(String(item)) + '</div>';
        }).join('');
      } else v = escapeHtml(String(value));
      return '<tr><td class="prop-key">' + escapeHtml(key) +
        '</td><td class="prop-val">' + v + '</td></tr>';
    },

    renderSources: function (sources, files) {
      var list = Array.isArray(sources) ? sources : (sources ? [sources] : []);
      var fileList = Array.isArray(files) ? files : (files ? [files] : []);
      if (!list.length && !fileList.length) {
        this.sourcesEl.innerHTML = '';
        this.sourcesEl.classList.add('hidden');
        return;
      }
      this.sourcesEl.classList.remove('hidden');
      var html = '';
      if (list.length) {
        html += '<div class="sources-label">Sources</div><ul>' +
          list.map(function (s) {
            return '<li>' + escapeHtml(String(s)) + '</li>';
          }).join('') + '</ul>';
      }
      if (fileList.length) {
        html += '<div class="sources-label" style="margin-top:8px">Resolved files</div><ul>' +
          fileList.map(function (s) {
            return '<li>' + escapeHtml(String(s)) + '</li>';
          }).join('') + '</ul>';
      }
      this.sourcesEl.innerHTML = html;
    }
  };

  /* ── In-page keybindings (ATLAS-KEYBINDINGS.md — implemented) ───
   * Smoke: /, arrows, Ctrl+arrows, Alt+Left/Right, WASD, l, t, e, v, i, o, m, ?, =/[ /], ., Enter,
   * Shift+Enter, Backspace, p, Esc. Ignore letter/nav while typing (except Esc, Ctrl+F).
   */
  var Keys = {
    handle: null,
    graphEl: null,
    navId: null,
    onToast: null,
    onOpenItem: null,
    _bound: null,
    helpers: null,

    init: function (opts) {
      opts = opts || {};
      this.handle = opts.handle || null;
      this.graphEl = opts.graphEl || document.getElementById('graph');
      this.onToast = opts.onToast || null;
      this.onOpenItem = opts.onOpenItem || null;
      this.onViewerToggle = opts.onViewerToggle || null;
      this.helpers = global.OkbayAtlasKeyHelpers || null;
      this.navId = null;
      if (this._bound) {
        window.removeEventListener('keydown', this._bound, true);
      }
      var self = this;
      this._bound = function (ev) { self.onKeyDown(ev); };
      // Capture on window so arrows work without canvas focus; filter editables.
      window.addEventListener('keydown', this._bound, true);
      this.focusCanvas();
      return this;
    },

    destroy: function () {
      if (this._bound) {
        window.removeEventListener('keydown', this._bound, true);
        this._bound = null;
      }
    },

    focusCanvas: function () {
      var canvas = this.mainCanvas();
      if (canvas && typeof canvas.focus === 'function') {
        try { canvas.focus({ preventScroll: true }); } catch (e) {
          try { canvas.focus(); } catch (e2) {}
        }
      }
    },

    mainCanvas: function () {
      if (!this.graphEl) return null;
      var nodes = this.graphEl.querySelectorAll('canvas');
      for (var i = 0; i < nodes.length; i++) {
        if (!nodes[i].classList.contains('atlas-minimap')) return nodes[i];
      }
      return nodes[0] || null;
    },

    engine: function () {
      return this.handle && this.handle.engine ? this.handle.engine : null;
    },

    isEditable: function (el) {
      if (this.helpers && this.helpers.isEditableTarget) {
        return this.helpers.isEditableTarget(el);
      }
      if (!el) return false;
      var tag = (el.tagName || '').toLowerCase();
      return tag === 'input' || tag === 'textarea' || tag === 'select' || !!el.isContentEditable;
    },

    hitNodes: function () {
      var eng = this.engine();
      if (!eng || !eng.hitTester || !eng.hitTester.nodes) return [];
      return eng.hitTester.nodes.map(function (n) {
        return { id: n.id, x: n.p.x, y: n.p.y };
      });
    },

    anchorId: function () {
      var eng = this.engine();
      if (!eng) return null;
      if (this.navId) return this.navId;
      var canvas = this.mainCanvas();
      var hover = canvas && canvas.dataset ? canvas.dataset.hoverId : '';
      if (hover) return hover;
      var st = eng.getState && eng.getState();
      return (st && st.focusId) || null;
    },

    softHighlight: function (id) {
      if (!id) return;
      this.navId = id;
      var eng = this.engine();
      if (!eng) return;
      try {
        if (typeof eng.hover === 'function') eng.hover(id);
        if (typeof eng.select === 'function') eng.select([id], 'replace');
      } catch (e) {}
      // Nudge IIFE hover ring via synthetic pointermove over the node.
      var nodes = this.hitNodes();
      var pt = null;
      for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].id === id) { pt = nodes[i]; break; }
      }
      var canvas = this.mainCanvas();
      if (!pt || !canvas) return;
      var rect = canvas.getBoundingClientRect();
      var clientX = rect.left + rect.width / 2 + pt.x;
      var clientY = rect.top + rect.height / 2 + pt.y;
      try {
        canvas.dispatchEvent(new PointerEvent('pointermove', {
          clientX: clientX,
          clientY: clientY,
          pointerId: 1,
          pointerType: 'mouse',
          bubbles: true,
          cancelable: true,
          view: window
        }));
      } catch (e) {}
    },

    hardFocus: function (id) {
      if (!id) return;
      this.navId = id;
      var eng = this.engine();
      if (!eng || typeof eng.focus !== 'function') return;
      try { eng.focus(id, 'user'); } catch (e) {}
      if (typeof this.onToast === 'function') this.onToast(id);
      try { Sidebar.setActive(id); } catch (e2) {}
    },

    graphNeighbourIds: function (anchorId) {
      var eng = this.engine();
      var ids = [];
      if (!eng || typeof eng.snapshot !== 'function') return ids;
      var snap = eng.snapshot();
      var scene = snap && snap.scene;
      if (!scene || !scene.edges) return ids;
      var seen = new Set();
      for (var i = 0; i < scene.edges.length; i++) {
        var e = scene.edges[i];
        var other = null;
        if (e.source === anchorId) other = e.target;
        else if (e.target === anchorId) other = e.source;
        if (other && !seen.has(other)) {
          seen.add(other);
          ids.push(other);
        }
      }
      return ids;
    },

    walkAngular: function (delta) {
      var H = this.helpers;
      var anchor = this.anchorId();
      var nodes = this.hitNodes();
      if (!anchor || !nodes.length || !H) return;
      var from = null;
      for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].id === anchor) { from = nodes[i]; break; }
      }
      if (!from) return;
      var neigh = this.graphNeighbourIds(anchor);
      var candidates;
      if (neigh.length) {
        var set = new Set(neigh);
        candidates = nodes.filter(function (n) { return set.has(n.id); });
      } else {
        // Fallback: visible nearby nodes (angular around focus).
        var maxR = 0;
        for (var j = 0; j < nodes.length; j++) {
          var dx = nodes[j].x - from.x, dy = nodes[j].y - from.y;
          var r = Math.hypot(dx, dy);
          if (r > maxR) maxR = r;
        }
        var lim = Math.max(80, maxR * 0.35);
        candidates = nodes.filter(function (n) {
          if (n.id === anchor) return false;
          return Math.hypot(n.x - from.x, n.y - from.y) <= lim;
        });
      }
      var ring = H.angularRing(from, candidates);
      var current = this.navId || anchor;
      // If current is the anchor itself, start from nearest ring member.
      var stepFrom = current === anchor && ring.length ? ring[0].id : current;
      var next = H.stepAngular(ring, stepFrom, delta);
      if (next && next !== current) this.softHighlight(next);
    },

    compass: function (dir) {
      var H = this.helpers;
      var nodes = this.hitNodes();
      if (!H || !nodes.length) return;
      // Stricter cone from viewport centre (0,0 in hitTester space).
      var next = H.nearestInDirectionFromPoint(nodes, 0, 0, dir, 1.15);
      if (next) this.softHighlight(next);
    },

    spatialStep: function (dir) {
      var eng = this.engine();
      var anchor = this.anchorId();
      if (!eng || !anchor || !eng.hitTester || typeof eng.hitTester.nearestInDirection !== 'function') {
        // Fallback: from centre if no focus yet.
        this.compass(dir);
        return;
      }
      var next = eng.hitTester.nearestInDirection(anchor, dir);
      if (next) this.softHighlight(next);
    },

    panBy: function (dx, dy) {
      var canvas = this.mainCanvas();
      if (!canvas) return;
      var rect = canvas.getBoundingClientRect();
      var x0 = rect.left + rect.width / 2;
      var y0 = rect.top + rect.height / 2;
      var opts = function (x, y, type) {
        return {
          clientX: x,
          clientY: y,
          pointerId: 42,
          pointerType: 'mouse',
          buttons: type === 'up' ? 0 : 1,
          button: 0,
          bubbles: true,
          cancelable: true,
          view: window
        };
      };
      try {
        canvas.dispatchEvent(new PointerEvent('pointerdown', opts(x0, y0, 'down')));
        canvas.dispatchEvent(new PointerEvent('pointermove', opts(x0 + dx, y0 + dy, 'move')));
        canvas.dispatchEvent(new PointerEvent('pointerup', opts(x0 + dx, y0 + dy, 'up')));
      } catch (e) {}
    },

    recenter: function () {
      var eng = this.engine();
      var H = this.helpers;
      if (!eng) return;
      var st = eng.getState && eng.getState();
      if (st && st.focusId) {
        this.hardFocus(st.focusId);
        return;
      }
      var nodes = this.hitNodes();
      if (!H || !nodes.length) return;
      var id = H.nearestToPoint(nodes, 0, 0);
      if (id) this.hardFocus(id);
    },

    onKeyDown: function (ev) {
      if (ev.defaultPrevented) return;
      // Super never reaches --app=; ignore meta anyway.
      if (ev.metaKey) return;

      var modalOpen = document.body.dataset.modal === 'open';
      var editable = this.isEditable(ev.target);
      var key = ev.key;
      var lower = key.length === 1 ? key.toLowerCase() : key;

      // Escape: help → modal → workspace → types → blur/clear search
      if (key === 'Escape') {
        if (Help.isOpen()) {
          Help.close();
          ev.preventDefault();
          return;
        }
        if (modalOpen) {
          Modal.close();
          ev.preventDefault();
          return;
        }
        if (Workspace.isOpen()) {
          Workspace.close();
          ev.preventDefault();
          return;
        }
        if (Controls.isTypesPanelOpen()) {
          Controls.closeTypesPanel();
          ev.preventDefault();
          return;
        }
        if (OkbayAtlasChrome.Views && OkbayAtlasChrome.Views.isPanelOpen && OkbayAtlasChrome.Views.isPanelOpen()) {
          OkbayAtlasChrome.Views.closePanel();
          ev.preventDefault();
          return;
        }
        if (editable && Sidebar.searchEl && (ev.target === Sidebar.searchEl || Sidebar.searchEl.contains(ev.target))) {
          Sidebar.blurSearch(true);
          this.focusCanvas();
          ev.preventDefault();
          return;
        }
        if (editable) {
          try { ev.target.blur(); } catch (e) {}
          this.focusCanvas();
          ev.preventDefault();
        }
        return;
      }

      // While modal open, only Esc (handled above).
      if (modalOpen) return;

      // Ctrl+F always focuses search (prevent Chromium find-in-page).
      if (ev.ctrlKey && !ev.altKey && (key === 'f' || key === 'F')) {
        Sidebar.focusSearch(true);
        ev.preventDefault();
        return;
      }

      // Slash focuses search when not already typing in an editable.
      if (key === '/' && !ev.ctrlKey && !ev.altKey) {
        if (editable) return;
        Sidebar.focusSearch(true);
        ev.preventDefault();
        return;
      }

      // Ignore remaining chords while typing in inputs (except we already handled Esc/Ctrl+F).
      if (editable) return;

      var H = this.helpers;
      var dir = H ? H.arrowDir(key) : null;

      // Ctrl+Arrow = compass from viewport centre
      if (ev.ctrlKey && !ev.altKey && dir) {
        this.compass(dir);
        ev.preventDefault();
        return;
      }

      // Alt+Arrow left/right = anticlockwise / clockwise neighbour walk
      if (ev.altKey && !ev.ctrlKey && (key === 'ArrowLeft' || key === 'ArrowRight')) {
        this.walkAngular(key === 'ArrowRight' ? 1 : -1);
        ev.preventDefault();
        return;
      }

      // Plain arrows = spatial nearestInDirection from current nav/focus
      if (!ev.ctrlKey && !ev.altKey && !ev.shiftKey && dir) {
        this.spatialStep(dir);
        ev.preventDefault();
        return;
      }

      // WASD pan (Shift = larger step). Not arrows.
      if (!ev.ctrlKey && !ev.altKey && (lower === 'w' || lower === 'a' || lower === 's' || lower === 'd')) {
        var step = ev.shiftKey ? 96 : 48;
        var dx = 0, dy = 0;
        if (lower === 'w') dy = step;
        if (lower === 's') dy = -step;
        if (lower === 'a') dx = step;
        if (lower === 'd') dx = -step;
        this.panBy(dx, dy);
        ev.preventDefault();
        return;
      }

      if (ev.ctrlKey || ev.altKey) return;

      if (key === '?' || (ev.shiftKey && key === '/')) {
        Help.toggle();
        ev.preventDefault();
        return;
      }
      if (lower === 'l') {
        Controls.cycleMode();
        ev.preventDefault();
        return;
      }
      if (lower === 't') {
        Controls.toggleTypesPanel();
        ev.preventDefault();
        return;
      }
      if (lower === 'e') {
        Controls.cycleEdgeMode();
        ev.preventDefault();
        return;
      }
      if (lower === 'v') {
        if (OkbayAtlasChrome.Views && typeof OkbayAtlasChrome.Views.togglePanel === 'function') {
          OkbayAtlasChrome.Views.togglePanel();
        } else if (typeof this.onViewerToggle === 'function') {
          this.onViewerToggle();
        }
        ev.preventDefault();
        return;
      }
      if (lower === 'i') {
        Ingest.promptAndIngest();
        ev.preventDefault();
        return;
      }
      if (lower === 'o') {
        Workspace.toggle();
        ev.preventDefault();
        return;
      }
      if (lower === 'm') {
        var shown = Controls.toggleMinimap();
        if (typeof this.onToast === 'function' && shown !== null) {
          this.onToast(shown ? 'minimap on' : 'minimap off');
        }
        ev.preventDefault();
        return;
      }
      if (key === '=' || key === '+') {
        Sidebar.toggleAllGroups();
        ev.preventDefault();
        return;
      }
      if (key === '[') {
        Sidebar.collapseAllGroups();
        ev.preventDefault();
        return;
      }
      if (key === ']') {
        Sidebar.expandAllGroups();
        ev.preventDefault();
        return;
      }
      if (key === '.') {
        this.recenter();
        ev.preventDefault();
        return;
      }
      if (key === 'Enter') {
        var id = this.navId || this.anchorId();
        if (!id) return;
        if (ev.shiftKey) {
          if (typeof this.onOpenItem === 'function') this.onOpenItem(id);
          else {
            var eng = this.engine();
            if (eng && typeof eng.openItem === 'function') eng.openItem(id);
          }
        } else {
          this.hardFocus(id);
        }
        ev.preventDefault();
        return;
      }
      if (key === 'Backspace') {
        var eng2 = this.engine();
        if (eng2 && typeof eng2.back === 'function') eng2.back();
        ev.preventDefault();
        return;
      }
      if (lower === 'p') {
        var pinId = this.navId || this.anchorId();
        var eng3 = this.engine();
        if (pinId && eng3 && typeof eng3.pin === 'function') eng3.pin(pinId);
        ev.preventDefault();
        return;
      }
    }
  };

  global.OkbayAtlasChrome = {
    Sidebar: Sidebar,
    Modal: Modal,
    Controls: Controls,
    Keys: Keys,
    Ingest: Ingest,
    Workspace: Workspace,
    Help: Help,
    VIEWER_KEY: VIEWER_KEY,
    canonicalType: canonicalType,
    applyPalette: applyPalette
  };
})(window);
