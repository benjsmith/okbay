//! Minimal HTTP/1.1 server. Same routes as src/okbay/server.py.
use crate::{atlas_ce, desks, graph, ingest, locate, paths, reviews, status, store, theme, wiki};
use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;

const ATLAS: &str = include_str!("../../../src/okbay/static/atlas.html");
const KNOWLEDGE_ATLAS_JS: &[u8] =
    include_bytes!("../../../src/okbay/static/vendor/knowledge-atlas.js");
const FUSE_JS: &[u8] = include_bytes!("../../../src/okbay/static/vendor/fuse.min.js");
const D3_JS: &[u8] = include_bytes!("../../../src/okbay/static/vendor/d3.min.js");
const ATLAS_CHROME_JS: &[u8] =
    include_bytes!("../../../src/okbay/static/atlas-chrome.js");
const ATLAS_KEYS_HELPERS_JS: &[u8] =
    include_bytes!("../../../src/okbay/static/atlas-keys-helpers.js");
const CLASSIC_GRAPH_JS: &[u8] =
    include_bytes!("../../../src/okbay/static/classic-graph.js");

pub fn serve(host: &str, port: u16) -> std::io::Result<()> {
    let ws = paths::ensure_workspace(None);
    let _ = store::reindex(&ws);
    let _ = graph::build(&ws);
    let _ = status::snapshot(&ws, Some("ready"));
    let listener = TcpListener::bind((host, port))?;
    eprintln!("okbayd listening on http://{host}:{port} workspace={}", ws.display());
    for stream in listener.incoming() {
        if let Ok(s) = stream { let _ = handle(s, &ws); }
    }
    Ok(())
}

fn handle(mut stream: TcpStream, ws: &PathBuf) -> std::io::Result<()> {
    let mut reader = BufReader::new(stream.try_clone()?);
    let mut line = String::new();
    reader.read_line(&mut line)?;
    let mut parts = line.split_whitespace();
    let method = parts.next().unwrap_or("GET").to_string();
    let raw = parts.next().unwrap_or("/").to_string();
    let (path, qs) = raw.split_once('?').map(|(p,q)| (p.to_string(), q.to_string())).unwrap_or((raw, String::new()));
    let mut content_length = 0usize;
    loop {
        line.clear();
        reader.read_line(&mut line)?;
        if line == "\r\n" || line == "\n" || line.is_empty() { break; }
        if let Some(v) = line.to_ascii_lowercase().strip_prefix("content-length:") {
            content_length = v.trim().parse().unwrap_or(0);
        }
    }
    let mut body = vec![0u8; content_length];
    if content_length > 0 { reader.read_exact(&mut body)?; }
    let q = |key: &str| -> String {
        qs.split('&').filter_map(|p| p.split_once('=')).find(|(k,_)| *k == key).map(|(_,v)| v.replace('+', " ")).unwrap_or_default()
    };
    if method == "GET" && (path == "/atlas" || path == "/") {
        return write_resp(&mut stream, 200, "text/html; charset=utf-8", ATLAS.as_bytes());
    }
    // Slice 1: vendored KnowledgeAtlas (+ Fuse for Slice 2).
    if method == "GET" && path == "/static/vendor/knowledge-atlas.js" {
        return write_resp(&mut stream, 200, "application/javascript", KNOWLEDGE_ATLAS_JS);
    }
    if method == "GET" && path == "/static/vendor/fuse.min.js" {
        return write_resp(&mut stream, 200, "application/javascript", FUSE_JS);
    }
    if method == "GET" && path == "/static/atlas-chrome.js" {
        return write_resp(&mut stream, 200, "application/javascript", ATLAS_CHROME_JS);
    }
    if method == "GET" && path == "/static/atlas-keys-helpers.js" {
        return write_resp(&mut stream, 200, "application/javascript", ATLAS_KEYS_HELPERS_JS);
    }
    if method == "GET" && path == "/static/classic-graph.js" {
        return write_resp(&mut stream, 200, "application/javascript", CLASSIC_GRAPH_JS);
    }
    if method == "GET" && path == "/static/vendor/d3.min.js" {
        return write_resp(&mut stream, 200, "application/javascript", D3_JS);
    }
    let payload: Value = if method == "GET" && path == "/health" {
        json!({"ok": true, "daemon": "rust"})
    } else if method == "GET" && (path == "/api/status" || path == "/status") {
        status::snapshot(ws, None)
    } else if method == "GET" && (path == "/api/theme" || path == "/theme") {
        theme::atlas_theme()
    } else if method == "GET" && (path == "/graph" || path == "/api/graph") {
        serde_json::to_value(graph::load(ws)).unwrap_or(json!({}))
    } else if method == "GET" && (path == "/api/search" || path == "/atlas/search") {
        json!({"hits": store::search(ws, &q("q"), 40)})
    } else if method == "GET" && path == "/api/reviews" {
        json!({"reviews": reviews::list(ws, &{
            let s = q("state"); if s.is_empty() { "pending".into() } else { s }
        })})
    } else if method == "GET" && (path == "/api/atlas/data" || path == "/atlas/data") {
        // CE Atlas data bridge (CuriosityDataSource / CEData). See atlas_ce.rs.
        atlas_ce::build_ce_data(ws)
    } else if method == "GET" && (path == "/api/locate" || path == "/locate") {
        // Accept stem= or legacy q=; reveal=0|false skips file-manager launch (atlas toast / resolve-only).
        let stem = { let s = q("stem"); if s.is_empty() { q("q") } else { s } };
        let rev = q("reveal");
        let reveal = !(rev == "0" || rev.eq_ignore_ascii_case("false") || rev.eq_ignore_ascii_case("no") || rev.eq_ignore_ascii_case("off"));
        locate::locate(ws, &stem, reveal)
    } else if method == "GET" && (path == "/api/atlas/page" || path == "/atlas/page") {
        // Slice 2: lazy wiki page for atlas modal.
        let stem = {
            let s = q("stem");
            if !s.is_empty() { s } else {
                let s = q("q");
                if s.is_empty() { q("id") } else { s }
            }
        };
        let wiki_dir = paths::wiki(ws);
        match wiki::page_payload(&wiki_dir, &stem) {
            Some(v) => v,
            None => json!({"error": "not found", "stem": stem}),
        }
    } else if method == "GET" && (path.starts_with("/api/wiki/") || path.starts_with("/wiki/")) {
        let stem = path.rsplit('/').next().unwrap_or("").to_string();
        let wiki_dir = paths::wiki(ws);
        match wiki::page_payload(&wiki_dir, &stem) {
            Some(v) => v,
            None => json!({"error": "not found", "stem": stem}),
        }
    } else if method == "POST" && path == "/api/rebuild" {
        let g = graph::build(ws);
        json!({"ok": true, "pages": g.pages, "nodes": g.nodes.len(), "links": g.edges.len()})
    } else if method == "POST" && path == "/api/ingest" {
        let body: Value = serde_json::from_slice(&body).unwrap_or(json!({}));
        ingest::ingest_path(ws, body.get("path").and_then(|v| v.as_str()).unwrap_or(""))
    } else if method == "POST" && path == "/api/propose" {
        let body: Value = serde_json::from_slice(&body).unwrap_or(json!({}));
        reviews::propose(ws, body["title"].as_str().unwrap_or(""), body["body"].as_str().unwrap_or(""), body["kind"].as_str().unwrap_or("note"), &[], "")
    } else if method == "POST" && path == "/api/review" {
        let body: Value = serde_json::from_slice(&body).unwrap_or(json!({}));
        reviews::resolve(ws, body["id"].as_i64().or_else(|| body["id"].as_str().and_then(|s| s.parse().ok())).unwrap_or(0), body["action"].as_str().unwrap_or("reject"), "")
    } else if method == "POST" && path == "/api/desk/start" {
        let body: Value = serde_json::from_slice(&body).unwrap_or(json!({}));
        desks::start(ws, body["kind"].as_str().unwrap_or("curate"), body["objective"].as_str().unwrap_or(""))
    } else if method == "GET" && (path == "/api/workspace" || path == "/api/workspace/list") {
        // Python workroot has full registry; Rust surfaces the active hub so chrome still boots.
        let hub = paths::default_workspace();
        json!({
            "work_root": hub.parent().map(|p| p.display().to_string()).unwrap_or_default(),
            "workspaces": { "okbay": hub.display().to_string() },
            "watch_roots": {},
            "active": "okbay",
            "current": ws.display().to_string(),
            "opt_out": [],
            "note": "named workspace registry is Python/okbayd; use python daemon for use/add/split"
        })
    } else if method == "POST" && path == "/api/workspace/use" {
        let body: Value = serde_json::from_slice(&body).unwrap_or(json!({}));
        let name = body.get("name").and_then(|v| v.as_str()).unwrap_or("okbay");
        if name == "okbay" {
            let hub = paths::ensure_workspace(Some(&paths::default_workspace()));
            json!({"ok": true, "name": "okbay", "workspace": hub.display().to_string(), "watch_roots": []})
        } else {
            json!({"ok": false, "error": format!("rust daemon: unknown workspace {name} (use python okbayd for named workspaces)")})
        }
    } else if method == "POST" && (path == "/api/workspace/add" || path == "/api/workspace/split") {
        json!({"ok": false, "error": "named workspace add/split requires python okbayd"})
    } else {
        json!({"error": "not found"})
    };
    let raw = serde_json::to_vec(&payload).unwrap_or_else(|_| b"{}".to_vec());
    write_resp(&mut stream, 200, "application/json", &raw)
}

fn write_resp(stream: &mut TcpStream, code: u16, ctype: &str, body: &[u8]) -> std::io::Result<()> {
    let status = if code == 200 { "OK" } else { "Error" };
    let head = format!("HTTP/1.1 {code} {status}\r\nContent-Type: {ctype}\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n", body.len());
    stream.write_all(head.as_bytes())?;
    stream.write_all(body)
}
