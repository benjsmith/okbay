/* Pure Atlas keyboard helpers — shared by atlas-chrome.js and unit tests.
 * No DOM. Safe in browser IIFE and Node (CommonJS / global).
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.OkbayAtlasKeyHelpers = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function isEditableTarget(el) {
    if (!el) return false;
    var doc = typeof document !== 'undefined' ? document : null;
    var win = typeof window !== 'undefined' ? window : null;
    if ((doc && el === doc) || (win && el === win)) return false;
    var tag = (el.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
    if (el.isContentEditable) return true;
    if (el.closest && el.closest('[contenteditable="true"]')) return true;
    return false;
  }

  /** Map KeyboardEvent.key Arrow* → direction token. */
  function arrowDir(key) {
    if (key === 'ArrowUp') return 'up';
    if (key === 'ArrowDown') return 'down';
    if (key === 'ArrowLeft') return 'left';
    if (key === 'ArrowRight') return 'right';
    return null;
  }

  /**
   * Spatial nearest in a cone from a point (viewport-centre compass).
   * Same scoring as engine hitTester.nearestInDirection.
   * @param {Array<{id:string,x:number,y:number}>} nodes
   * @param {number} ox
   * @param {number} oy
   * @param {'up'|'down'|'left'|'right'} dir
   * @param {number} [cone=1.5] ortho/along max ratio
   */
  function nearestInDirectionFromPoint(nodes, ox, oy, dir, cone) {
    cone = cone == null ? 1.5 : cone;
    var best = null;
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      var dx = n.x - ox;
      var dy = n.y - oy;
      var along = dir === 'right' ? dx : dir === 'left' ? -dx : dir === 'down' ? dy : -dy;
      var ortho = dir === 'right' || dir === 'left' ? Math.abs(dy) : Math.abs(dx);
      if (along <= 0 || ortho > along * cone) continue;
      var d = along + ortho * 0.5;
      if (!best || d < best.d) best = { id: n.id, d: d };
    }
    return best ? best.id : null;
  }

  /**
   * Build angular ring around anchor from candidate nodes.
   * @param {{x:number,y:number}} anchor
   * @param {Array<{id:string,x:number,y:number}>} candidates
   * @returns {Array<{id:string,angle:number}>}
   */
  function angularRing(anchor, candidates) {
    var ring = [];
    for (var i = 0; i < candidates.length; i++) {
      var n = candidates[i];
      ring.push({
        id: n.id,
        angle: Math.atan2(n.y - anchor.y, n.x - anchor.x)
      });
    }
    ring.sort(function (a, b) {
      return a.angle - b.angle || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
    });
    return ring;
  }

  /**
   * Step ±1 in a sorted angular ring (clockwise = +1).
   * @param {Array<{id:string}>} ring
   * @param {string|null} currentId
   * @param {number} delta  +1 clockwise, -1 anticlockwise
   */
  function stepAngular(ring, currentId, delta) {
    if (!ring || !ring.length) return null;
    var idx = 0;
    if (currentId) {
      for (var i = 0; i < ring.length; i++) {
        if (ring[i].id === currentId) { idx = i; break; }
      }
    }
    var next = (idx + delta) % ring.length;
    if (next < 0) next += ring.length;
    return ring[next].id;
  }

  /** Pick node nearest to (ox, oy). */
  function nearestToPoint(nodes, ox, oy) {
    var best = null;
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      var d = (n.x - ox) * (n.x - ox) + (n.y - oy) * (n.y - oy);
      if (!best || d < best.d) best = { id: n.id, d: d };
    }
    return best ? best.id : null;
  }

  return {
    isEditableTarget: isEditableTarget,
    arrowDir: arrowDir,
    nearestInDirectionFromPoint: nearestInDirectionFromPoint,
    angularRing: angularRing,
    stepAngular: stepAngular,
    nearestToPoint: nearestToPoint
  };
});
