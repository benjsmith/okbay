use crate::paths;
use crate::wiki::list_pages;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashSet;
use std::fs;
use std::path::Path;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Node {
    pub id: String,
    pub title: String,
    pub kind: String,
    pub path: String,
    pub sources: Vec<String>,
    pub files: Vec<String>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Edge {
    pub source: String,
    pub target: String,
    #[serde(rename = "type")]
    pub kind: String,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Graph {
    pub nodes: Vec<Node>,
    pub edges: Vec<Edge>,
    pub pages: usize,
}

pub fn build(ws: &Path) -> Graph {
    let pages = list_pages(&paths::wiki(ws));
    let mut nodes = vec![];
    let mut edges = vec![];
    let mut stems: HashSet<String> = pages.iter().map(|p| p.stem.clone()).collect();
    let vault = paths::vault(ws);
    for p in &pages {
        let files: Vec<String> = p.sources.iter().map(|s| {
            let cand = Path::new(s);
            if cand.is_absolute() { cand.to_path_buf() } else { vault.join(s) }
        }).filter(|c| c.exists()).map(|c| c.to_string_lossy().to_string()).collect();
        nodes.push(Node { id: p.stem.clone(), title: p.title.clone(), kind: p.kind.clone(), path: p.path.to_string_lossy().to_string(), sources: p.sources.clone(), files });
        for dest in &p.links {
            let slug = dest.trim().to_string();
            edges.push(Edge { source: p.stem.clone(), target: slug.clone(), kind: "wikilink".into() });
            if stems.insert(slug.clone()) {
                nodes.push(Node { id: slug.clone(), title: slug, kind: "missing".into(), path: String::new(), sources: vec![], files: vec![] });
            }
        }
    }
    let g = Graph { pages: pages.len(), nodes, edges };
    if let Some(parent) = paths::graph_json(ws).parent() { let _ = fs::create_dir_all(parent); }
    let _ = fs::write(paths::graph_json(ws), serde_json::to_string_pretty(&g).unwrap_or_else(|_| "{}".into()));
    g
}
pub fn load(ws: &Path) -> Graph {
    let path = paths::graph_json(ws);
    if let Ok(text) = fs::read_to_string(&path) {
        if let Ok(g) = serde_json::from_str::<Graph>(&text) { return g; }
    }
    build(ws)
}
pub fn search(g: &Graph, query: &str) -> Vec<Value> {
    let q = query.trim().to_lowercase();
    g.nodes.iter().filter(|n| {
        if q.is_empty() { return true; }
        format!("{} {} {} {}", n.id, n.title, n.kind, n.sources.join(" ")).to_lowercase().contains(&q)
    }).take(40).map(|n| json!({"id": n.id, "stem": n.id, "title": n.title, "kind": n.kind, "path": n.path, "files": n.files})).collect()
}
