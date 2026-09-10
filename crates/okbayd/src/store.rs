use crate::paths;
use crate::wiki::{list_pages, slugify, write_page};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::fs;
use std::path::Path;

#[derive(Clone, Debug, Serialize)]
pub struct Hit { pub stem: String, pub title: String, pub kind: String, pub path: String }

pub fn reviews_json(ws: &Path) -> std::path::PathBuf { ws.join(".okbay/reviews.json") }

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Review {
    pub id: i64,
    pub stem: String,
    pub title: String,
    pub body: String,
    #[serde(default)] pub kind: String,
    #[serde(default)] pub sources: Vec<String>,
    #[serde(default)] pub reviewer_note: String,
    #[serde(default = "pending")] pub status: String,
    #[serde(default)] pub created_at: String,
}
fn pending() -> String { "pending".into() }

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
struct ReviewFile { #[serde(default)] next_id: i64, #[serde(default)] reviews: Vec<Review> }

fn load_reviews(ws: &Path) -> ReviewFile {
    let p = reviews_json(ws);
    if let Ok(text) = fs::read_to_string(&p) {
        if let Ok(f) = serde_json::from_str::<ReviewFile>(&text) { return f; }
        if let Ok(list) = serde_json::from_str::<Vec<Review>>(&text) {
            let next = list.iter().map(|r| r.id).max().unwrap_or(0) + 1;
            return ReviewFile { next_id: next, reviews: list };
        }
    }
    ReviewFile { next_id: 1, reviews: vec![] }
}
fn save_reviews(ws: &Path, file: &ReviewFile) {
    let p = reviews_json(ws);
    if let Some(parent) = p.parent() { let _ = fs::create_dir_all(parent); }
    let _ = fs::write(p, serde_json::to_string_pretty(file).unwrap_or_else(|_| "{}".into()));
}
pub fn reindex(ws: &Path) -> usize { list_pages(&paths::wiki(ws)).len() }
pub fn search(ws: &Path, query: &str, limit: usize) -> Vec<Hit> {
    let q = query.trim().to_lowercase();
    let mut out = vec![];
    for p in list_pages(&paths::wiki(ws)) {
        if q.is_empty() || p.stem.to_lowercase().contains(&q) || p.title.to_lowercase().contains(&q) || p.body.to_lowercase().contains(&q) {
            out.push(Hit { stem: p.stem, title: p.title, kind: p.kind, path: p.path.to_string_lossy().to_string() });
            if out.len() >= limit { break; }
        }
    }
    out
}
pub fn pending_count(ws: &Path) -> i64 { load_reviews(ws).reviews.iter().filter(|r| r.status == "pending").count() as i64 }
pub fn list_reviews(ws: &Path, state: &str) -> Vec<Value> {
    load_reviews(ws).reviews.into_iter().filter(|r| state == "all" || r.status == state).map(|r| serde_json::to_value(r).unwrap_or(json!({}))).collect()
}
pub fn propose(ws: &Path, title: &str, body: &str, kind: &str, sources: &[String], note: &str) -> Value {
    let mut file = load_reviews(ws);
    let id = if file.next_id <= 0 { 1 } else { file.next_id };
    file.next_id = id + 1;
    let rec = Review { id, stem: slugify(title), title: title.into(), body: body.into(), kind: kind.into(), sources: sources.to_vec(), reviewer_note: note.into(), status: "pending".into(), created_at: String::new() };
    file.reviews.push(rec.clone());
    save_reviews(ws, &file);
    serde_json::to_value(rec).unwrap_or(json!({"id": id, "status": "pending"}))
}
pub fn resolve(ws: &Path, id: i64, action: &str, _note: &str) -> Value {
    let mut file = load_reviews(ws);
    let action = action.to_lowercase();
    if let Some(rec) = file.reviews.iter_mut().find(|r| r.id == id) {
        rec.status = if action == "accept" { "accepted".into() } else { "rejected".into() };
        let out = rec.clone();
        if action == "accept" {
            write_page(&paths::wiki(ws), &out.stem, &out.title, &out.body, &out.kind, &out.sources);
        }
        save_reviews(ws, &file);
        return serde_json::to_value(out).unwrap_or(json!({}));
    }
    json!({"error": format!("review {id} not found")})
}
