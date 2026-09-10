use crate::paths;
use crate::wiki::{slugify, write_page};
use serde_json::{json, Value};
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};

pub fn ingest_path(ws: &Path, src: &str) -> Value {
    let src_path = PathBuf::from(src).canonicalize().unwrap_or_else(|_| PathBuf::from(src));
    if !src_path.exists() {
        return json!({"ok": false, "error": format!("missing {src}")});
    }
    let vault = paths::vault(ws);
    let _ = fs::create_dir_all(&vault);
    let name = src_path.file_name().and_then(|s| s.to_str()).unwrap_or("file");
    let dest = vault.join(name);
    if dest != src_path {
        let _ = fs::copy(&src_path, &dest);
    }
    let preview = preview(&dest);
    let title = dest.file_stem().and_then(|s| s.to_str()).unwrap_or("file").replace(['_', '-'], " ");
    let stem = slugify(&title);
    let fname = dest.file_name().and_then(|s| s.to_str()).unwrap_or("file").to_string();
    let page = write_page(&paths::wiki(ws), &stem, &title, &format!("Captured from `{fname}`.\n\n```\n{preview}\n```\n"), "source", &[fname.clone()]);
    json!({"ok": true, "vault": dest.to_string_lossy(), "page": page.path.to_string_lossy(), "stem": page.stem, "title": page.title})
}
fn preview(path: &Path) -> String {
    let mut f = match fs::File::open(path) { Ok(f) => f, Err(e) => return format!("(unreadable: {e})") };
    let mut buf = vec![0u8; 2048];
    let n = f.read(&mut buf).unwrap_or(0);
    buf.truncate(n);
    if buf.iter().take(1024).any(|b| *b == 0) { return format!("(binary, {n} bytes)"); }
    String::from_utf8_lossy(&buf).chars().take(2000).collect()
}
