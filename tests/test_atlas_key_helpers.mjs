/**
 * Unit tests for atlas-keys-helpers.js (pure spatial / angular keyboard helpers).
 * Run: node tests/test_atlas_key_helpers.mjs
 */
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const require = createRequire(import.meta.url);
const __dirname = dirname(fileURLToPath(import.meta.url));
const H = require(join(__dirname, '../src/okbay/static/atlas-keys-helpers.js'));

function assert(cond, msg) {
  if (!cond) throw new Error(msg || 'assertion failed');
}

function almost(a, b, eps = 1e-9) {
  return Math.abs(a - b) < eps;
}

// arrowDir
assert(H.arrowDir('ArrowUp') === 'up');
assert(H.arrowDir('ArrowLeft') === 'left');
assert(H.arrowDir('x') === null);

// nearestInDirectionFromPoint — cross layout around origin
const nodes = [
  { id: 'origin', x: 0, y: 0 },
  { id: 'right', x: 40, y: 2 },
  { id: 'left', x: -40, y: -1 },
  { id: 'up', x: 1, y: -40 },
  { id: 'down', x: -2, y: 40 },
  { id: 'far-right', x: 200, y: 0 },
];
assert(H.nearestInDirectionFromPoint(nodes, 0, 0, 'right') === 'right');
assert(H.nearestInDirectionFromPoint(nodes, 0, 0, 'left') === 'left');
assert(H.nearestInDirectionFromPoint(nodes, 0, 0, 'up') === 'up');
assert(H.nearestInDirectionFromPoint(nodes, 0, 0, 'down') === 'down');
// Stricter cone should reject wide diagonal for pure right
assert(H.nearestInDirectionFromPoint(
  [{ id: 'a', x: 10, y: 40 }, { id: 'b', x: 40, y: 2 }],
  0, 0, 'right', 1.15
) === 'b');

// nearestToPoint
assert(H.nearestToPoint(nodes, 1, 1) === 'origin');

// angularRing + stepAngular (clockwise = +1)
const ringNodes = [
  { id: 'e', x: 10, y: 0 },
  { id: 'n', x: 0, y: -10 },
  { id: 'w', x: -10, y: 0 },
  { id: 's', x: 0, y: 10 },
];
const ring = H.angularRing({ x: 0, y: 0 }, ringNodes);
assert(ring.length === 4);
// atan2 order: n (-π/2), e (0), s (π/2), w (π) roughly — verify step wraps
const ids = ring.map((r) => r.id);
assert(ids.includes('e') && ids.includes('n') && ids.includes('w') && ids.includes('s'));
const afterE = H.stepAngular(ring, 'e', 1);
const beforeE = H.stepAngular(ring, 'e', -1);
assert(afterE && afterE !== 'e');
assert(beforeE && beforeE !== 'e');
assert(afterE !== beforeE);
// full cycle returns to start
let cur = 'e';
for (let i = 0; i < ring.length; i++) cur = H.stepAngular(ring, cur, 1);
assert(cur === 'e', 'clockwise full cycle should return to start');

console.log('ok — atlas key helpers (' + [
  'arrowDir', 'nearestInDirectionFromPoint', 'nearestToPoint', 'angularRing', 'stepAngular'
].join(', ') + ')');
