/* Slim classic D3 force graph for Okbay Atlas ↔ Graph toggle.
 * CE-shaped CEData (nodes/edges/palette). Caps large corpora for usability.
 */
(function (global) {
  'use strict';

  var MAX_NODES = 2500;
  var MAX_EDGES = 8000;

  function ClassicGraph() {
    this.svg = null;
    this.simulation = null;
    this.zoom = null;
    this.nodeById = new Map();
    this.focusId = null;
    this.onOpen = null;
    this.container = null;
    this._ro = null;
  }

  ClassicGraph.prototype.init = function (container, data, opts) {
    opts = opts || {};
    this.destroy();
    this.container = container;
    this.onOpen = opts.onOpen || null;
    if (!global.d3 || !container) return this;

    var nodesIn = Array.isArray(data.nodes) ? data.nodes.slice() : [];
    var edgesIn = Array.isArray(data.edges) ? data.edges.slice() : [];
    var palette = data.palette || {};
    var truncated = false;
    if (nodesIn.length > MAX_NODES) {
      truncated = true;
      nodesIn.sort(function (a, b) { return (b.degree || 0) - (a.degree || 0); });
      nodesIn = nodesIn.slice(0, MAX_NODES);
    }
    var keep = new Set(nodesIn.map(function (n) { return n.id; }));
    edgesIn = edgesIn.filter(function (e) {
      var s = typeof e.source === 'object' ? e.source.id : e.source;
      var t = typeof e.target === 'object' ? e.target.id : e.target;
      return keep.has(s) && keep.has(t);
    });
    if (edgesIn.length > MAX_EDGES) {
      truncated = true;
      edgesIn = edgesIn.slice(0, MAX_EDGES);
    }

    var nodes = nodesIn.map(function (n) {
      return {
        id: n.id,
        title: n.title || n.id,
        type: n.type || n.kind || 'note',
        degree: n.degree || 0
      };
    });
    this.nodeById = new Map(nodes.map(function (n) { return [n.id, n]; }));
    var links = edgesIn.map(function (e) {
      return {
        source: typeof e.source === 'object' ? e.source.id : e.source,
        target: typeof e.target === 'object' ? e.target.id : e.target,
        type: e.type || 'wikilink'
      };
    });

    var w = container.clientWidth || 800;
    var h = container.clientHeight || 600;
    var svg = global.d3.select(container).append('svg')
      .attr('width', '100%')
      .attr('height', '100%')
      .attr('class', 'classic-graph')
      .style('display', 'block')
      .style('background', 'transparent');
    this.svg = svg;

    var g = svg.append('g').attr('class', 'zoom-surface');
    var linkG = g.append('g').attr('class', 'links');
    var nodeG = g.append('g').attr('class', 'nodes');

    var self = this;
    this.zoom = global.d3.zoom().scaleExtent([0.05, 8]).on('zoom', function (ev) {
      g.attr('transform', ev.transform);
    });
    svg.call(this.zoom);

    var link = linkG.selectAll('line').data(links).join('line')
      .attr('stroke', 'var(--line, #343942)')
      .attr('stroke-opacity', 0.35)
      .attr('stroke-width', 1);

    var node = nodeG.selectAll('circle').data(nodes, function (d) { return d.id; }).join('circle')
      .attr('r', function (d) { return 3 + Math.min(8, Math.sqrt((d.degree || 0) + 1)); })
      .attr('fill', function (d) { return palette[d.type] || palette.default || '#6be8b3'; })
      .attr('stroke', 'transparent')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .call(global.d3.drag()
        .on('start', function (ev, d) {
          if (!ev.active) self.simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', function (ev, d) { d.fx = ev.x; d.fy = ev.y; })
        .on('end', function (ev, d) {
          if (!ev.active) self.simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        }))
      .on('click', function (ev, d) {
        ev.stopPropagation();
        self.focus(d.id);
        if (typeof self.onOpen === 'function') self.onOpen(d.id);
      })
      .on('dblclick', function (ev, d) {
        ev.stopPropagation();
        if (typeof self.onOpen === 'function') self.onOpen(d.id);
      });

    node.append('title').text(function (d) { return d.title; });

    this.simulation = global.d3.forceSimulation(nodes)
      .force('link', global.d3.forceLink(links).id(function (d) { return d.id; }).distance(48).strength(0.4))
      .force('charge', global.d3.forceManyBody().strength(-80).distanceMax(400))
      .force('center', global.d3.forceCenter(0, 0))
      .force('collide', global.d3.forceCollide().radius(function (d) {
        return 4 + Math.min(8, Math.sqrt((d.degree || 0) + 1));
      }))
      .on('tick', function () {
        link
          .attr('x1', function (d) { return d.source.x; })
          .attr('y1', function (d) { return d.source.y; })
          .attr('x2', function (d) { return d.target.x; })
          .attr('y2', function (d) { return d.target.y; });
        node.attr('cx', function (d) { return d.x; }).attr('cy', function (d) { return d.y; });
      });

    svg.call(this.zoom.transform, global.d3.zoomIdentity.translate(w / 2, h / 2).scale(
      nodes.length > 800 ? 0.35 : nodes.length > 200 ? 0.55 : 0.9
    ));

    this._nodeSel = node;
    this._linkSel = link;
    this._truncated = truncated;
    this._counts = { nodes: nodes.length, edges: links.length, total: (data.nodes || []).length };

    this._ro = new ResizeObserver(function () {
      /* layout stays world-centred; nothing to recompute */
    });
    this._ro.observe(container);
    return this;
  };

  ClassicGraph.prototype.focus = function (id) {
    this.focusId = id;
    if (!this._nodeSel) return;
    var self = this;
    this._nodeSel
      .attr('stroke', function (d) { return d.id === self.focusId ? 'var(--accent, #6be8b3)' : 'transparent'; })
      .attr('stroke-width', function (d) { return d.id === self.focusId ? 3 : 2; })
      .attr('opacity', function (d) {
        if (!self.focusId) return 1;
        return d.id === self.focusId ? 1 : 0.35;
      });
    if (this._linkSel) {
      this._linkSel.attr('stroke-opacity', function (d) {
        if (!self.focusId) return 0.35;
        var s = d.source.id || d.source;
        var t = d.target.id || d.target;
        return (s === self.focusId || t === self.focusId) ? 0.85 : 0.08;
      });
    }
  };

  ClassicGraph.prototype.clearFocus = function () {
    this.focusId = null;
    this.focus(null);
  };

  ClassicGraph.prototype.destroy = function () {
    if (this._ro) { try { this._ro.disconnect(); } catch (e) {} this._ro = null; }
    if (this.simulation) { this.simulation.stop(); this.simulation = null; }
    if (this.container) {
      var svg = this.container.querySelector('svg.classic-graph');
      if (svg) svg.remove();
    }
    this.svg = null;
    this._nodeSel = null;
    this._linkSel = null;
  };

  global.OkbayClassicGraph = ClassicGraph;
})(window);
