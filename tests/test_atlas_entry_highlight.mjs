// Mounts the vendored Atlas engine in a minimal stub DOM and checks that no
// node or edge stays highlighted when nothing is focused, selected or hovered.
//
// With no focus the engine builds its first scene around a well-connected
// entry node. That node used to keep the "focus" role and its edges kept
// highlight priority, so it looked selected and stayed lit after every
// clear (and came back on each scene rebuild).
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(
  path.join(here, "..", "src", "okbay", "static", "vendor", "knowledge-atlas.js"),
  "utf8",
);

function stub(extra = {}) {
  const target = function () {};
  Object.assign(target, extra);
  return new Proxy(target, {
    get(t, k) {
      if (k in t) return t[k];
      if (k === Symbol.toPrimitive) return () => 0;
      if (k === "then") return undefined;
      return stub();
    },
    set(t, k, v) { t[k] = v; return true; },
    apply() { return stub(); },
    construct() { return stub(); },
  });
}

function element(tag) {
  const listeners = {};
  return stub({
    tagName: String(tag || "div").toUpperCase(),
    style: {},
    dataset: {},
    clientWidth: 1200,
    clientHeight: 800,
    width: 1200,
    height: 800,
    children: [],
    appendChild(c) { this.children.push(c); return c; },
    removeChild() {},
    remove() {},
    addEventListener(type, fn) { (listeners[type] ||= []).push(fn); },
    removeEventListener() {},
    dispatch(type, ev) { for (const fn of listeners[type] || []) fn(ev || {}); },
    getBoundingClientRect() { return { left: 0, top: 0, width: 1200, height: 800, right: 1200, bottom: 800 }; },
    getContext() { return stub({ measureText: () => ({ width: 10 }) }); },
    setAttribute() {},
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
  });
}

const rafQueue = [];
const ctx = {
  console,
  Math, JSON, Date, Map, Set, WeakMap, Array, Object, Number, String, Promise, Symbol, Error,
  Float32Array, Float64Array, Uint8Array, Uint32Array, Int32Array, ArrayBuffer,
  DOMException: globalThis.DOMException,
  AbortController: globalThis.AbortController,
  performance: globalThis.performance,
  setTimeout: (fn) => { rafQueue.push(fn); return rafQueue.length; },
  clearTimeout() {},
  setInterval: () => 0,
  clearInterval() {},
  requestAnimationFrame: (fn) => { rafQueue.push(() => fn(performance.now())); return rafQueue.length; },
  cancelAnimationFrame() {},
  getComputedStyle: () => ({ position: "relative", getPropertyValue: () => "" }),
  ResizeObserver: class { observe() {} disconnect() {} unobserve() {} },
  MutationObserver: class { observe() {} disconnect() {} },
  devicePixelRatio: 1,
};
ctx.window = ctx;
ctx.globalThis = ctx;
ctx.document = {
  documentElement: element("html"),
  body: element("body"),
  createElement: (t) => element(t),
  addEventListener() {},
  removeEventListener() {},
};
ctx.window.addEventListener = () => {};
ctx.window.removeEventListener = () => {};
vm.createContext(ctx);
vm.runInContext(src, ctx);

// A hub with many links plus a chain of sources, like a people-heavy wiki.

const HUB = "entities/aaron-pottier";
const nodes = [{ id: HUB, title: "[ent] Aaron Pottier", type: "entity", degree: 40 }];
const pages = { [HUB]: { id: HUB, title: "[ent] Aaron Pottier", type: "entity", properties: { sources: ["a", "b", "c"] } } };
const edges = [];
for (let i = 0; i < 40; i++) {
  const id = `sources/doc-${i}`;
  nodes.push({ id, title: `[src] Doc ${i}`, type: "source", degree: 3 });
  pages[id] = { id, title: `[src] Doc ${i}`, type: "source", properties: {} };
  edges.push({ source: HUB, target: id, type: "mentions" });
  if (i > 0) edges.push({ source: id, target: `sources/doc-${i - 1}`, type: "related" });
}

const host = element("div");
const handle = ctx.KnowledgeAtlas.mount(host, {
  data: { nodes, edges, pages },
  config: { layout: "hybrid", corpusSize: nodes.length, coreCapacity: nodes.length, maxVisibleNodes: nodes.length,
            budget: { maxNodes: nodes.length, maxAggregates: 0, maxEdges: 900 } },
});

async function settle() {
  for (let round = 0; round < 20; round++) {
    await new Promise((r) => setImmediate(r));
    const q = rafQueue.splice(0, rafQueue.length);
    for (const fn of q) { try { fn(); } catch (e) { /* render stubs */ } }
  }
}

function lit(snap) {
  const scene = snap.scene;
  return {
    focusNodes: scene.nodes.filter((n) => n.role === "focus").map((n) => n.id),
    priorityEdges: scene.edges.filter((e) => e.priority === 1).length,
  };
}

let failures = 0;
function check(label, cond, detail) {
  if (!cond) { failures++; console.log("FAIL", label, detail ?? ""); }
  else console.log("ok  ", label);
}

await settle();
const eng = handle.engine;
let snap = eng.snapshot();
check("engine is idle", eng.getState ? !eng.errorMsg : true, eng.errorMsg);
check("scene built", !!snap.scene && snap.scene.nodes.length === nodes.length, snap.scene && snap.scene.nodes.length);
let s = lit(snap);
check("no focus at start → no focus node", s.focusNodes.length === 0, JSON.stringify(s));
check("no focus at start → no lit edges", s.priorityEdges === 0, JSON.stringify(s));

eng.focus("sources/doc-5", "user");
await settle();
s = lit(eng.snapshot());
check("focus marks the focused node", s.focusNodes.join() === "sources/doc-5", JSON.stringify(s));
check("focus lights only its own edges", s.priorityEdges > 0 && s.priorityEdges <= 3, JSON.stringify(s));

eng.focus(HUB, "user");
await settle();
s = lit(eng.snapshot());
check("refocus moves the highlight", s.focusNodes.join() === HUB && s.priorityEdges === 40, JSON.stringify(s));

handle.clearHighlights();
await settle();
s = lit(eng.snapshot());
check("clearHighlights drops focus node", s.focusNodes.length === 0, JSON.stringify(s));
check("clearHighlights drops lit edges", s.priorityEdges === 0, JSON.stringify(s));

// A rebuild with nothing focused (resize / zoom band change) must not bring
// the entry node's highlight back.
eng.resize(1000, 700);
eng.zoomTo(eng.getState().semanticScale + 1);
eng.zoomTo(eng.getState().semanticScale - 1);
await settle();
s = lit(eng.snapshot());
check("rebuild with no focus stays clear", s.focusNodes.length === 0 && s.priorityEdges === 0, JSON.stringify(s));

handle.destroy && (() => { try { handle.destroy(); } catch (e) {} })();
if (failures) { console.log(`${failures} failure(s)`); process.exit(1); }
console.log("ok — atlas entry highlight");
