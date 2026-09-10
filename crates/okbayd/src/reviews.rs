use crate::store;
use serde_json::Value;
use std::path::Path;

pub fn propose(ws: &Path, title: &str, body: &str, kind: &str, sources: &[String], note: &str) -> Value {
    store::propose(ws, title, body, kind, sources, note)
}
pub fn list(ws: &Path, state: &str) -> Vec<Value> {
    store::list_reviews(ws, state)
}
pub fn resolve(ws: &Path, id: i64, action: &str, note: &str) -> Value {
    store::resolve(ws, id, action, note)
}
