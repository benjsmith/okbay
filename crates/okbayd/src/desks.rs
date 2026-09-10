use crate::paths;
use serde_json::{json, Value};
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

const KINDS: &[&str] = &["curate", "work", "code", "deck"];

fn load(ws: &Path) -> Value {
    let p = paths::desks_path(ws);
    if let Ok(text) = fs::read_to_string(p) {
        if let Ok(v) = serde_json::from_str::<Value>(&text) { return v; }
    }
    json!({"active": null, "history": []})
}
fn save(ws: &Path, data: &Value) {
    let p = paths::desks_path(ws);
    if let Some(parent) = p.parent() { let _ = fs::create_dir_all(parent); }
    let _ = fs::write(p, serde_json::to_string_pretty(data).unwrap_or_else(|_| "{}".into()));
}
pub fn start(ws: &Path, kind: &str, objective: &str) -> Value {
    let kind = kind.trim().to_lowercase();
    if !KINDS.contains(&kind.as_str()) {
        return json!({"ok": false, "error": format!("unknown desk {kind}")});
    }
    let layout = match kind.as_str() {
        "curate" => "n=1", "work" => "hsl 2", "code" => "hdl", "deck" => "web-app", _ => "",
    };
    let seated = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0);
    let desk = json!({"id": kind, "state": "working", "objective": objective, "seated_at": seated, "layout": layout});
    let mut data = load(ws);
    data["active"] = desk.clone();
    save(ws, &data);
    desk
}
pub fn stop(ws: &Path) -> Value {
    let mut data = load(ws);
    if !data["active"].is_null() { data["active"]["state"] = json!("quiet"); }
    save(ws, &data);
    data["active"].clone()
}
pub fn status(ws: &Path) -> Value {
    load(ws).get("active").cloned().unwrap_or(json!(null))
}
