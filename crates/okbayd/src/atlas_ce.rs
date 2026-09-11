//! CE Atlas data bridge — CEData JSON for CuriosityDataSource / KnowledgeAtlas.
//! Slice 0: canvas payload (stub body_html). Endpoint: GET /api/atlas/data
use crate::{graph, paths, theme};
use serde_json::{json, Map, Value};
use std::collections::{HashMap, HashSet};
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

fn normalize_id(id: &str) -> String {
    let s = id.trim();
    if let Some(stripped) = s.strip_suffix(".md") {
        stripped.to_string()
    } else {
        s.to_string()
    }
}

fn canonical_type(raw: &str, title: &str) -> String {
    let key = raw.trim().to_lowercase().replace(' ', "-");
    let mapped = match key.as_str() {
        "analysis" | "analyses" => Some("analysis"),
        "concept" | "concepts" => Some("concept"),
        "entity" | "entities" => Some("entity"),
        "evidence" => Some("evidence"),
        "fact" | "facts" => Some("fact"),
        "figure" | "figures" => Some("figure"),
        "table" | "tables" | "extracted-table" | "summary-table" => Some("table"),
        "source" | "sources" | "source-note" => Some("source"),
        "note" | "notes" => Some("note"),
        "todo" | "todo-list" => Some("todo-list"),
        "project" | "projects" => Some("project"),
        "hub" => Some("hub"),
        "missing" => Some("missing"),
        "unclassified" => Some("unclassified"),
        _ => None,
    };
    if let Some(m) = mapped {
        if m != "unclassified" {
            return m.to_string();
        }
    }
    // Title prefix backfill: "[con] Foo"
    let t = title.trim();
    if let Some(rest) = t.strip_prefix('[') {
        if let Some(end) = rest.find(']') {
            let stem = rest[..end].trim().to_lowercase();
            let back = match stem.as_str() {
                "con" => Some("concept"),
                "ent" => Some("entity"),
                "ana" => Some("analysis"),
                "src" => Some("source"),
                "evi" => Some("evidence"),
                "fact" => Some("fact"),
                "tbl" | "tab" => Some("table"),
                "fig" => Some("figure"),
                "note" => Some("note"),
                "todo" => Some("todo-list"),
                "proj" => Some("project"),
                _ => None,
            };
            if let Some(b) = back {
                return b.to_string();
            }
        }
    }
    if key == "hub" || key == "missing" {
        return key;
    }
    mapped.unwrap_or("unclassified").to_string()
}

fn is_file_id(id: &str) -> bool {
    id.starts_with("file:")
}

fn iso_now_or_mtime(ws: &Path) -> String {
    let path = paths::graph_json(ws);
    if let Ok(meta) = std::fs::metadata(&path) {
        if let Ok(mtime) = meta.modified() {
            if let Ok(dur) = mtime.duration_since(UNIX_EPOCH) {
                return format_iso(dur.as_secs());
            }
        }
    }
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format_iso(now)
}

fn format_iso(secs: u64) -> String {
    // Minimal UTC ISO8601 without chrono dependency.
    const SECS_PER_DAY: u64 = 86400;
    const DAYS_PER_CYCLE: u64 = 146097; // 400y
    const SECS_PER_HOUR: u64 = 3600;
    let days = secs / SECS_PER_DAY;
    let tod = secs % SECS_PER_DAY;
    let hh = tod / SECS_PER_HOUR;
    let mm = (tod % SECS_PER_HOUR) / 60;
    let ss = tod % 60;
    // Civil from days since 1970-01-01 (Howard Hinnant algorithm).
    let z = days + 719468;
    let era = z / DAYS_PER_CYCLE;
    let doe = z - era * DAYS_PER_CYCLE;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = (yoe as i64) + (era as i64) * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z", y, m, d, hh, mm, ss)
}

/// Build CEData-compatible JSON from the okbay graph + theme palette.
pub fn build_ce_data(ws: &Path) -> Value {
    let g = graph::load(ws);
    let theme_val = theme::atlas_theme();
    let palette = theme_val
        .get("types")
        .or_else(|| theme_val.get("kinds"))
        .cloned()
        .unwrap_or_else(|| json!({}));
    // Prefer graph kind (wiki parse folds frontmatter type:→kind on rebuild).
    // Avoid re-listing the whole wiki on every /api/atlas/data hit (Biocure ~40k).
    let mut degree: HashMap<String, i64> = HashMap::new();
    let mut edges_out: Vec<Value> = Vec::new();
    for e in &g.edges {
        let src = normalize_id(&e.source);
        let tgt = normalize_id(&e.target);
        if src.is_empty() || tgt.is_empty() || is_file_id(&src) || is_file_id(&tgt) {
            continue;
        }
        edges_out.push(json!({"source": src, "target": tgt, "type": e.kind}));
        *degree.entry(normalize_id(&e.source)).or_insert(0) += 1;
        *degree.entry(normalize_id(&e.target)).or_insert(0) += 1;
    }

    let mut nodes_out: Vec<Value> = Vec::new();
    let mut pages_out = Map::new();
    let mut seen = HashSet::new();
    for n in &g.nodes {
        let nid = normalize_id(&n.id);
        if nid.is_empty() || is_file_id(&nid) || !seen.insert(nid.clone()) {
            continue;
        }
        let title = if n.title.is_empty() {
            nid.clone()
        } else {
            n.title.clone()
        };
        let ntype = canonical_type(&n.kind, &title);
        let deg = *degree.get(&nid).unwrap_or(&0);
        nodes_out.push(json!({
            "id": nid,
            "path": n.path,
            "type": ntype,
            "title": title,
            "degree": deg,
        }));
        pages_out.insert(
            nid.clone(),
            json!({
                "id": nid,
                "title": title,
                "type": ntype,
                "path": n.path,
                "properties": {"sources": n.sources, "files": n.files},
                "sources": n.sources,
                "files": n.files,
                "body_html": "",
            }),
        );
    }

    json!({
        "workspace": ws.display().to_string(),
        "generated_at": iso_now_or_mtime(ws),
        "palette": palette,
        "nodes": nodes_out,
        "edges": edges_out,
        "pages": pages_out,
        "page_count": g.pages,
    })
}
