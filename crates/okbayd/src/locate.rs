use crate::paths;
use crate::wiki::get_page;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::process::Command;

pub fn locate(ws: &Path, stem: &str) -> Value {
    let page = match get_page(&paths::wiki(ws), stem) {
        Some(p) => p,
        None => return json!({"ok": false, "error": format!("no page {stem}")}),
    };
    let mut resolved = vec![];
    for src in &page.sources {
        let p = Path::new(src);
        let full = if p.is_absolute() { p.to_path_buf() } else { paths::vault(ws).join(src) };
        resolved.push(full.to_string_lossy().to_string());
    }
    let target = resolved.first().cloned().unwrap_or_else(|| page.path.to_string_lossy().to_string());
    if std::env::var("OKBAY_REVEAL").unwrap_or_else(|_| "1".into()) != "0" {
        if let Some(dir) = PathBuf::from(&target).parent() {
            let _ = Command::new("xdg-open").arg(dir).spawn();
        }
    }
    json!({"ok": true, "stem": page.stem, "title": page.title, "wiki": page.path.to_string_lossy(), "sources": resolved})
}
