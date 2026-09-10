use crate::desks;
use crate::graph;
use crate::paths;
use crate::store;
use serde_json::{json, Value};
use std::fs;
use std::time::{SystemTime, UNIX_EPOCH};

pub fn snapshot(ws: &std::path::Path, state: Option<&str>) -> Value {
    let now = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0);
    let g = graph::load(ws);
    let ready = paths::wiki(ws).is_dir();
    let st = state.unwrap_or(if ready { "ready" } else { "setup" });
    let payload = json!({
        "ts": now,
        "state": st,
        "pages": g.pages,
        "nodes": g.nodes.len(),
        "reviews_pending": store::pending_count(ws),
        "desk": desks::status(ws),
        "atlas_url": "http://127.0.0.1:8766/atlas",
        "api_url": "http://127.0.0.1:8766",
        "workspace": ws.to_string_lossy(),
        "version": "0.1.0",
        "daemon": "okbayd-rust",
    });
    let _ = fs::write(paths::status_path(), serde_json::to_string_pretty(&payload).unwrap_or_default());
    payload
}
pub fn invalidate() {}
