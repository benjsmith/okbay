use crate::paths;
use crate::wiki::get_page;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::process::Command;

pub fn locate(ws: &Path, stem: &str, reveal: bool) -> Value {
    let page = match get_page(&paths::wiki(ws), stem) {
        Some(p) => p,
        None => return json!({"ok": false, "error": format!("no page {stem}")}),
    };
    let vault = paths::vault(ws);
    let mut resolved = vec![];
    let mut existing = vec![];
    for src in &page.sources {
        let p = Path::new(src);
        let full = if p.is_absolute() {
            p.to_path_buf()
        } else {
            let cand = vault.join(src);
            if cand.exists() {
                cand
            } else {
                ws.join(src)
            }
        };
        let s = full.to_string_lossy().to_string();
        if full.exists() {
            existing.push(s.clone());
        }
        resolved.push(s);
    }
    let target = existing
        .first()
        .cloned()
        .or_else(|| resolved.first().cloned())
        .unwrap_or_else(|| page.path.to_string_lossy().to_string());
    let mut out = json!({
        "ok": true,
        "stem": page.stem,
        "title": page.title,
        "wiki": page.path.to_string_lossy(),
        "sources": resolved,
        "files": existing,
        "kind": page.kind,
        "target": target,
        "revealed": Value::Null,
    });
    if reveal {
        if let Some(dir) = PathBuf::from(&target).parent() {
            if dir.exists() {
                match Command::new("xdg-open").arg(dir).spawn() {
                    Ok(_) => {
                        out["revealed"] = json!(["xdg-open", dir.to_string_lossy()]);
                    }
                    Err(_) => {
                        out["reveal_error"] = json!("xdg-open failed");
                    }
                }
            } else {
                out["reveal_error"] = json!("path missing");
            }
        }
    }
    out
}
