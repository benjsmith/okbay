/* Workspace-scoped views shell for the Atlas host.
 * Replaces classic/atlas toggle with a views popup (Atlas, Viewer, Table, …).
 * Attaches to window.OkbayAtlasChrome.Views when chrome is present.
 */
(function (global) {
  'use strict';

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, '&#39;');
  }

  function parseHash() {
    var raw = (location.hash || '').replace(/^#/, '');
    var out = { view: 'atlas', page: '', source: '' };
    if (!raw) return out;
    if (raw.indexOf('page=') === 0 && raw.indexOf('view=') < 0) {
      out.page = decodeURIComponent(raw.slice(5).split('&')[0] || '');
      out.view = out.page ? 'viewer' : 'atlas';
      return out;
    }
    raw.split('&').forEach(function (part) {
      var i = part.indexOf('=');
      if (i < 0) return;
      var k = decodeURIComponent(part.slice(0, i));
      var v = decodeURIComponent(part.slice(i + 1));
      if (k === 'view') out.view = v || 'atlas';
      if (k === 'page') out.page = v;
      if (k === 'source') out.source = v;
    });
    return out;
  }

  function writeHash(state, replace) {
    var parts = ['view=' + encodeURIComponent(state.view || 'atlas')];
    if (state.page) parts.push('page=' + encodeURIComponent(state.page));
    if (state.source) parts.push('source=' + encodeURIComponent(state.source));
    var next = '#' + parts.join('&');
    if (location.hash === next) return;
    if (replace) history.replaceState(null, '', next);
    else location.hash = next;
  }

  var Views = {
    api: '',
    current: 'atlas',
    stickyPage: null,
    history: [],
    historyIdx: -1,
    pages: null,
    dynamic: [],
    ceData: null,
    opts: null,

    init: function (ceData, opts) {
      this.ceData = ceData || {};
      this.opts = opts || {};
      this.api = (opts && opts.api) || location.origin;
      var self = this;
      var btn = document.getElementById('viewer-mode');
      var panel = document.getElementById('views-panel');
      if (btn) {
        btn.classList.remove('hidden');
        btn.hidden = false;
        btn.title = 'Switch view (v)';
        btn.setAttribute('aria-label', 'Switch view');
        btn.addEventListener('click', function (ev) {
          ev.stopPropagation();
          self.togglePanel();
        });
      }
      if (panel) {
        panel.addEventListener('click', function (ev) {
          var row = ev.target.closest && ev.target.closest('[data-view-id]');
          if (!row) return;
          ev.preventDefault();
          self.closePanel();
          self.setView(row.getAttribute('data-view-id'), { page: self.stickyPage });
        });
      }
      document.addEventListener('click', function (ev) {
        if (!panel || panel.classList.contains('hidden')) return;
        if (panel.contains(ev.target)) return;
        if (btn && (ev.target === btn || btn.contains(ev.target))) return;
        panel.classList.add('hidden');
      });
      var back = document.getElementById('viewer-back');
      var fwd = document.getElementById('viewer-forward');
      if (back) back.addEventListener('click', function () { self.historyBack(); });
      if (fwd) fwd.addEventListener('click', function () { self.historyForward(); });
      var acceptAll = document.getElementById('reviews-accept-all');
      if (acceptAll) {
        acceptAll.addEventListener('click', function () { self.acceptAllReviews(); });
      }
      window.addEventListener('hashchange', function () { self.applyHash(); });
      this.refreshMenu().then(function () {
        self.applyHash({ initial: true });
      });
      return this;
    },

    isPanelOpen: function () {
      var panel = document.getElementById('views-panel');
      return !!(panel && !panel.classList.contains('hidden'));
    },

    closePanel: function () {
      var panel = document.getElementById('views-panel');
      if (panel) panel.classList.add('hidden');
    },

    togglePanel: function () {
      var panel = document.getElementById('views-panel');
      if (!panel) return false;
      var open = panel.classList.contains('hidden');
      panel.classList.toggle('hidden');
      if (open) this.refreshMenu();
      return open;
    },

    refreshMenu: function () {
      var self = this;
      var list = document.getElementById('views-panel-list');
      return fetch(this.api + '/api/views')
        .then(function (r) { return r.json(); })
        .then(function (doc) {
          var views = (doc && doc.views) || [];
          self.dynamic = views.filter(function (v) { return !v.builtin; });
          if (!list) return;
          list.innerHTML = views.map(function (v) {
            var extra = v.id === 'reviews' && v.pending
              ? ' <span class="views-badge">' + escapeHtml(String(v.pending)) + '</span>'
              : '';
            var active = v.id === self.current ? ' data-active="true"' : '';
            return '<button type="button" class="views-row" data-view-id="' +
              escapeAttr(v.id) + '"' + active + '>' +
              escapeHtml(v.title || v.id) + extra + '</button>';
          }).join('') || '<div class="sidebar-empty">No views</div>';
          var state = document.getElementById('viewer-mode-state');
          if (state) {
            var cur = views.find(function (v) { return v.id === self.current; });
            state.textContent = (cur && cur.title) || self.current;
          }
        })
        .catch(function () {
          if (list) list.innerHTML = '<div class="sidebar-empty">Failed to load views</div>';
        });
    },

    setView: function (id, opts) {
      opts = opts || {};
      id = id || 'atlas';
      this.current = id;
      document.documentElement.dataset.view = id;
      document.body.dataset.view = id;
      var sidebar = document.getElementById('sidebar');
      var graphPane = document.getElementById('graph-pane');
      var viewPane = document.getElementById('view-pane');
      var controlsEl = document.getElementById('graph-controls');
      var appEl = document.getElementById('app');
      var atlasChrome = id === 'atlas';
      if (sidebar) {
        sidebar.hidden = !atlasChrome;
        sidebar.classList.toggle('hidden', !atlasChrome);
      }
      if (graphPane) {
        // Keep pane in layout for controls positioning; hide only the canvas.
        var graph = document.getElementById('graph');
        var status = document.getElementById('status');
        if (graph) {
          graph.hidden = !atlasChrome;
          graph.style.display = atlasChrome ? '' : 'none';
        }
        if (status) status.style.display = atlasChrome ? '' : 'none';
        graphPane.classList.toggle('view-host', !atlasChrome);
      }
      if (viewPane) {
        viewPane.classList.toggle('hidden', atlasChrome);
        viewPane.hidden = atlasChrome;
        if (!atlasChrome && graphPane && viewPane.parentElement !== graphPane) {
          // Place view-pane inside graph-pane so it fills the right area.
          graphPane.appendChild(viewPane);
        }
        if (atlasChrome && appEl && viewPane.parentElement !== appEl) {
          appEl.appendChild(viewPane);
        }
      }
      // Views button always available; atlas-only controls hide off-atlas.
      if (controlsEl && appEl) {
        // Pin controls to app so they survive pane swaps.
        appEl.appendChild(controlsEl);
        controlsEl.style.position = 'fixed';
        controlsEl.style.bottom = '14px';
        controlsEl.style.left = atlasChrome ? 'calc(var(--sidebar-w) + 14px)' : '14px';
        controlsEl.style.zIndex = '40';
      }
      ['label-mode', 'edge-mode', 'label-types'].forEach(function (bid) {
        var el = document.getElementById(bid);
        if (el) el.classList.toggle('hidden', !atlasChrome);
      });
      var typesPanel = document.getElementById('label-types-panel');
      if (typesPanel && !atlasChrome) typesPanel.classList.add('hidden');
      var page = opts.page != null ? opts.page : this.stickyPage;
      if (id === 'viewer' && page) this.stickyPage = page;
      if (!opts.skipHash) {
        writeHash({
          view: id,
          page: id === 'viewer' ? (page || '') : (opts.keepPage ? page : ''),
          source: opts.source || ''
        }, !!opts.replaceHash);
      }
      this.render(id, opts);
      this.refreshMenu();
      if (typeof this.opts.onViewChange === 'function') {
        this.opts.onViewChange(id, opts);
      }
    },

    applyHash: function (opts) {
      opts = opts || {};
      var h = parseHash();
      if (h.page) this.stickyPage = h.page;
      this.setView(h.view || 'atlas', {
        page: h.page,
        source: h.source,
        skipHash: true,
        replaceHash: !!opts.initial
      });
    },

    openPage: function (pageId, opts) {
      opts = opts || {};
      if (!pageId) return;
      // Sticky: selecting another doc replaces; empty click must not clear (caller).
      this.pushHistory(pageId, opts.source || null);
      this.stickyPage = pageId;
      if (this.current !== 'viewer' || opts.forceView) {
        this.setView('viewer', { page: pageId, source: opts.source || '', replaceHash: !!opts.replaceHash });
      } else {
        writeHash({ view: 'viewer', page: pageId, source: opts.source || '' }, !!opts.replaceHash);
        this.renderViewer(pageId, opts.source || '');
      }
    },

    pushHistory: function (pageId, source) {
      var entry = { page: pageId, source: source || '' };
      if (this.historyIdx >= 0) {
        var cur = this.history[this.historyIdx];
        if (cur && cur.page === entry.page && cur.source === entry.source) return;
      }
      this.history = this.history.slice(0, this.historyIdx + 1);
      this.history.push(entry);
      this.historyIdx = this.history.length - 1;
      this.paintHistoryButtons();
    },

    historyBack: function () {
      if (this.historyIdx <= 0) return;
      this.historyIdx -= 1;
      var e = this.history[this.historyIdx];
      this.stickyPage = e.page;
      this.setView('viewer', { page: e.page, source: e.source, skipHistory: true });
      this.paintHistoryButtons();
    },

    historyForward: function () {
      if (this.historyIdx >= this.history.length - 1) return;
      this.historyIdx += 1;
      var e = this.history[this.historyIdx];
      this.stickyPage = e.page;
      this.setView('viewer', { page: e.page, source: e.source, skipHistory: true });
      this.paintHistoryButtons();
    },

    paintHistoryButtons: function () {
      var back = document.getElementById('viewer-back');
      var fwd = document.getElementById('viewer-forward');
      if (back) back.disabled = this.historyIdx <= 0;
      if (fwd) fwd.disabled = this.historyIdx >= this.history.length - 1 || this.history.length === 0;
    },

    ensurePages: function () {
      var self = this;
      if (this.pages) return Promise.resolve(this.pages);
      // Prefer CE nodes already loaded; fall back to /api/views/pages.
      var nodes = (this.ceData && this.ceData.nodes) || [];
      if (nodes.length) {
        this.pages = nodes.map(function (n) {
          return {
            id: n.id || n.stem,
            stem: n.stem || n.id,
            title: n.title || n.id,
            kind: n.kind || n.type || 'note',
            type: n.type || n.kind || 'note'
          };
        });
        return Promise.resolve(this.pages);
      }
      return fetch(this.api + '/api/views/pages?limit=20000')
        .then(function (r) { return r.json(); })
        .then(function (doc) {
          self.pages = (doc && doc.pages) || [];
          return self.pages;
        })
        .catch(function () {
          self.pages = [];
          return self.pages;
        });
    },

    render: function (id, opts) {
      opts = opts || {};
      var host = document.getElementById('view-pane-body');
      if (!host && id !== 'atlas') return;
      if (id === 'atlas') return;
      if (id === 'viewer') {
        this.renderViewer(opts.page || this.stickyPage, opts.source || '');
        return;
      }
      if (id === 'table') return this.renderTable(host);
      if (id === 'library') return this.renderFiltered(host, 'library', function (p) {
        var t = (p.type || p.kind || '').toLowerCase();
        return t === 'source' || t === 'figure' || t === 'table' || t === 'vault';
      });
      if (id === 'projects') return this.renderFiltered(host, 'projects', function (p) {
        return (p.type || p.kind || '').toLowerCase() === 'project';
      });
      if (id === 'reviews') return this.renderReviews(host);
      // Dynamic
      this.renderDynamic(host, id);
    },

    renderViewer: function (pageId, source) {
      var host = document.getElementById('view-pane-body');
      var titleEl = document.getElementById('view-pane-title');
      var chrome = document.getElementById('viewer-nav');
      if (chrome) chrome.classList.remove('hidden');
      this.paintHistoryButtons();
      if (!host) return;
      // Source mode: render vault file body (sticky wiki page kept in hash/history).
      if (source) {
        this.renderSourceBody(host, source, pageId || this.stickyPage || '');
        return;
      }
      if (!pageId) {
        if (titleEl) titleEl.textContent = 'Viewer';
        host.innerHTML = '<div class="view-empty">Select a page from Atlas (double-click) or open from a list. Selection is sticky — empty clicks do not clear.</div>';
        return;
      }
      if (titleEl) titleEl.textContent = pageId;
      host.innerHTML = '<p class="modal-loading">Loading…</p>';
      var self = this;
      var url = this.api + '/api/atlas/page?stem=' + encodeURIComponent(pageId);
      fetch(url)
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          if (!res.ok) {
            host.innerHTML = '<p class="modal-empty">Not found: ' + escapeHtml(pageId) + '</p>';
            return;
          }
          var doc = res.j;
          if (titleEl) titleEl.textContent = doc.title || doc.stem || pageId;
          var props = '';
          var sources = doc.sources || (doc.properties && doc.properties.sources) || [];
          if (sources && sources.length) {
            props += '<div class="viewer-sources"><div class="views-section-head">Sources</div>' +
              sources.map(function (s) {
                return '<button type="button" class="viewer-source-btn" data-source="' +
                  escapeAttr(String(s)) + '">' + escapeHtml(String(s)) + '</button>';
              }).join('') + '</div>';
          }
          var body = doc.body_html || ('<pre class="viewer-md">' + escapeHtml(doc.markdown || '') + '</pre>');
          host.innerHTML =
            '<div class="viewer-meta">' + escapeHtml(doc.type || doc.kind || '') +
            (doc.path ? ' · <code>' + escapeHtml(doc.path) + '</code>' : '') + '</div>' +
            props +
            '<div class="viewer-body">' + body + '</div>';
          host.querySelectorAll('.viewer-source-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
              var src = btn.getAttribute('data-source');
              self.openSource(src, pageId);
            });
          });
          host.querySelectorAll('a.wikilink[data-page]').forEach(function (a) {
            a.addEventListener('click', function (ev) {
              ev.preventDefault();
              self.openPage(a.getAttribute('data-page'));
            });
          });
        })
        .catch(function (e) {
          host.innerHTML = '<p class="modal-empty">Failed: ' + escapeHtml(String(e)) + '</p>';
        });
    },

    openSource: function (sourcePath, fromPage) {
      // Switch Viewer to source rendering in the same view (sticky page retained).
      var page = fromPage || this.stickyPage || '';
      if (page) this.stickyPage = page;
      this.pushHistory(page, sourcePath);
      writeHash({ view: 'viewer', page: page, source: sourcePath });
      var host = document.getElementById('view-pane-body');
      if (!host) return;
      this.renderSourceBody(host, sourcePath, page);
    },

    renderSourceBody: function (host, sourcePath, fromPage) {
      var titleEl = document.getElementById('view-pane-title');
      if (titleEl) titleEl.textContent = 'Source · ' + sourcePath;
      host.innerHTML = '<p class="modal-loading">Loading source…</p>';
      var self = this;
      var url = this.api + '/api/atlas/source?path=' + encodeURIComponent(sourcePath);
      if (fromPage) url += '&stem=' + encodeURIComponent(fromPage);
      fetch(url)
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, j: j }; }); })
        .then(function (res) {
          if (!res.ok) {
            var err = (res.j && res.j.error) || ('HTTP ' + res.status);
            host.innerHTML =
              '<div class="viewer-meta">source file</div>' +
              '<pre class="viewer-md">' + escapeHtml(sourcePath) + '</pre>' +
              '<p class="modal-empty">' + escapeHtml(err) + '</p>' +
              '<p><button type="button" class="modal-action-btn" id="viewer-back-to-page">Back to page</button></p>';
            self._bindBackToPage(fromPage);
            return;
          }
          var doc = res.j;
          if (titleEl) titleEl.textContent = 'Source · ' + (doc.title || sourcePath);
          var body = doc.body_html || ('<pre class="viewer-md">' + escapeHtml(doc.markdown || '') + '</pre>');
          var pathLabel = doc.relpath || doc.path || sourcePath;
          host.innerHTML =
            '<div class="viewer-meta">' + escapeHtml(doc.kind || 'source') +
            ' · <code>' + escapeHtml(pathLabel) + '</code></div>' +
            '<div class="viewer-body">' + body + '</div>' +
            '<p><button type="button" class="modal-action-btn" id="viewer-back-to-page">Back to page</button></p>';
          host.querySelectorAll('a.wikilink[data-page]').forEach(function (a) {
            a.addEventListener('click', function (ev) {
              ev.preventDefault();
              self.openPage(a.getAttribute('data-page'));
            });
          });
          self._bindBackToPage(fromPage);
        })
        .catch(function (e) {
          host.innerHTML = '<p class="modal-empty">Failed: ' + escapeHtml(String(e)) + '</p>';
        });
    },

    _bindBackToPage: function (fromPage) {
      var self = this;
      var btn = document.getElementById('viewer-back-to-page');
      if (btn) btn.addEventListener('click', function () {
        self.openPage(fromPage || self.stickyPage);
      });
    },

    renderTable: function (host) {
      var chrome = document.getElementById('viewer-nav');
      if (chrome) chrome.classList.add('hidden');
      var titleEl = document.getElementById('view-pane-title');
      if (titleEl) titleEl.textContent = 'Table';
      host.innerHTML = '<p class="modal-loading">Loading…</p>';
      var self = this;
      this.ensurePages().then(function (pages) {
        var rows = pages.map(function (p) {
          return '<tr data-id="' + escapeAttr(p.id || p.stem) + '">' +
            '<td>' + escapeHtml(p.title || p.stem) + '</td>' +
            '<td>' + escapeHtml(p.kind || '') + '</td>' +
            '<td>' + escapeHtml(p.type || '') + '</td></tr>';
        }).join('');
        host.innerHTML =
          '<div class="views-toolbar">' + pages.length + ' pages</div>' +
          '<div class="views-table-wrap"><table class="views-table">' +
          '<thead><tr><th>Title</th><th>Kind</th><th>Type</th></tr></thead>' +
          '<tbody>' + rows + '</tbody></table></div>';
        host.querySelectorAll('tbody tr[data-id]').forEach(function (tr) {
          tr.addEventListener('click', function () {
            self.openPage(tr.getAttribute('data-id'));
          });
        });
      });
    },

    renderFiltered: function (host, title, pred) {
      var chrome = document.getElementById('viewer-nav');
      if (chrome) chrome.classList.add('hidden');
      var titleEl = document.getElementById('view-pane-title');
      if (titleEl) titleEl.textContent = title.charAt(0).toUpperCase() + title.slice(1);
      host.innerHTML = '<p class="modal-loading">Loading…</p>';
      var self = this;
      this.ensurePages().then(function (pages) {
        var filtered = pages.filter(pred);
        if (!filtered.length) {
          host.innerHTML = '<div class="view-empty">No matching pages.</div>';
          return;
        }
        host.innerHTML =
          '<div class="views-toolbar">' + filtered.length + '</div>' +
          '<div class="views-list">' +
          filtered.map(function (p) {
            return '<button type="button" class="views-list-row" data-id="' +
              escapeAttr(p.id || p.stem) + '"><span class="dot" data-type="' +
              escapeAttr(p.type || p.kind || 'note') + '"></span>' +
              '<span>' + escapeHtml(p.title || p.stem) + '</span>' +
              '<span class="views-list-meta">' + escapeHtml(p.type || p.kind || '') + '</span></button>';
          }).join('') + '</div>';
        host.querySelectorAll('.views-list-row').forEach(function (btn) {
          btn.addEventListener('click', function () {
            self.openPage(btn.getAttribute('data-id'));
          });
        });
      });
    },

    renderReviews: function (host) {
      var chrome = document.getElementById('viewer-nav');
      if (chrome) chrome.classList.add('hidden');
      var titleEl = document.getElementById('view-pane-title');
      if (titleEl) titleEl.textContent = 'Reviews';
      host.innerHTML = '<p class="modal-loading">Loading…</p>';
      var self = this;
      fetch(this.api + '/api/reviews?state=pending')
        .then(function (r) { return r.json(); })
        .then(function (doc) {
          var rows = (doc && doc.reviews) || [];
          if (!rows.length) {
            host.innerHTML = '<div class="view-empty">No pending reviews.</div>';
            self.setView('atlas', { replaceHash: true });
            return;
          }
          host.innerHTML =
            '<div class="views-toolbar">' +
            '<span>' + rows.length + ' pending</span>' +
            '<button type="button" class="modal-action-btn" id="reviews-accept-all-inline">Accept All</button>' +
            '</div>' +
            '<div class="views-list">' +
            rows.map(function (r) {
              return '<div class="views-list-row static">' +
                '<strong>' + escapeHtml(r.title || r.stem || r.id) + '</strong>' +
                '<span class="views-list-meta">' + escapeHtml(r.kind || '') + ' · #' + escapeHtml(String(r.id)) + '</span>' +
                '<span class="reviews-actions">' +
                '<button type="button" data-accept="' + escapeAttr(String(r.id)) + '">Accept</button>' +
                '<button type="button" data-reject="' + escapeAttr(String(r.id)) + '">Reject</button>' +
                '</span></div>';
            }).join('') + '</div>';
          var aa = document.getElementById('reviews-accept-all-inline');
          if (aa) aa.addEventListener('click', function () { self.acceptAllReviews(); });
          host.querySelectorAll('[data-accept]').forEach(function (btn) {
            btn.addEventListener('click', function () {
              self.resolveReview(btn.getAttribute('data-accept'), 'accept');
            });
          });
          host.querySelectorAll('[data-reject]').forEach(function (btn) {
            btn.addEventListener('click', function () {
              self.resolveReview(btn.getAttribute('data-reject'), 'reject');
            });
          });
        })
        .catch(function (e) {
          host.innerHTML = '<p class="modal-empty">Failed: ' + escapeHtml(String(e)) + '</p>';
        });
    },

    resolveReview: function (id, action) {
      var self = this;
      fetch(this.api + '/api/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id, action: action })
      }).then(function () { self.renderReviews(document.getElementById('view-pane-body')); self.refreshMenu(); });
    },

    acceptAllReviews: function () {
      var self = this;
      fetch(this.api + '/api/reviews/accept-all', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
        .then(function (r) { return r.json(); })
        .then(function () {
          self.refreshMenu().then(function () {
            // Hide Reviews when empty — fall back to Atlas.
            self.setView('atlas', { replaceHash: true });
          });
        });
    },

    renderDynamic: function (host, id) {
      var chrome = document.getElementById('viewer-nav');
      if (chrome) chrome.classList.add('hidden');
      var titleEl = document.getElementById('view-pane-title');
      var meta = (this.dynamic || []).find(function (v) { return v.id === id; });
      if (titleEl) titleEl.textContent = (meta && meta.title) || id;
      var src = (meta && meta.url) || ('/views/' + encodeURIComponent(id));
      // Sandboxed iframe: no parent script access.
      host.innerHTML =
        '<iframe class="views-frame" title="' + escapeAttr((meta && meta.title) || id) + '" ' +
        'sandbox="allow-scripts allow-same-origin allow-forms" referrerpolicy="no-referrer" ' +
        'src="' + escapeAttr(src) + '"></iframe>';
    }
  };

  global.OkbayViewsShell = Views;
  if (global.OkbayAtlasChrome) {
    global.OkbayAtlasChrome.Views = Views;
  } else {
    document.addEventListener('DOMContentLoaded', function () {
      if (global.OkbayAtlasChrome) global.OkbayAtlasChrome.Views = Views;
    });
  }
})(typeof window !== 'undefined' ? window : globalThis);
