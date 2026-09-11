//! Markdown pages with YAML-ish frontmatter and [[wikilinks]].
use serde::Serialize;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, Serialize)]
pub struct Page {
    pub stem: String,
    pub path: PathBuf,
    pub title: String,
    pub kind: String,
    pub body: String,
    pub links: Vec<String>,
    pub sources: Vec<String>,
}

pub fn slugify(title: &str) -> String {
    let mut out = String::new();
    for ch in title.trim().to_lowercase().chars() {
        if ch.is_ascii_alphanumeric() { out.push(ch); }
        else if !out.ends_with('-') && !out.is_empty() { out.push('-'); }
    }
    let s = out.trim_matches('-').to_string();
    if s.is_empty() { "page".into() } else { s }
}

fn extract_wikilinks(body: &str) -> Vec<String> {
    let mut links = Vec::new();
    let bytes = body.as_bytes();
    let mut i = 0;
    while i + 1 < bytes.len() {
        if bytes[i] == b'[' && bytes[i + 1] == b'[' {
            if let Some(rel) = body[i + 2..].find("]]") {
                let inner = &body[i + 2..i + 2 + rel];
                let dest = inner.split('|').next().unwrap_or(inner);
                let dest = dest.split('#').next().unwrap_or(dest).trim();
                if !dest.is_empty() { links.push(dest.to_string()); }
                i += 4 + rel;
                continue;
            }
        }
        i += 1;
    }
    links
}

fn parse_front(raw: &str) -> std::collections::BTreeMap<String, String> {
    let mut meta = std::collections::BTreeMap::new();
    for line in raw.lines() {
        if let Some((k, v)) = line.split_once(':') {
            meta.insert(k.trim().to_string(), v.trim().trim_matches('"').trim_matches('\'').to_string());
        }
    }
    meta
}

fn parse_list(val: &str) -> Vec<String> {
    let t = val.trim();
    if t.starts_with('[') && t.ends_with(']') {
        t[1..t.len()-1].split(',').map(|p| p.trim().trim_matches('"').trim_matches('\'').to_string()).filter(|s| !s.is_empty()).collect()
    } else if t.is_empty() { vec![] } else { vec![t.to_string()] }
}

pub fn parse_page(path: &Path) -> Option<Page> {
    let raw = fs::read_to_string(path).ok()?;
    let stem_default = path.file_stem()?.to_string_lossy().to_string();
    let mut title = stem_default.replace('-', " ");
    let mut kind = "note".to_string();
    let mut stem = stem_default.clone();
    let mut body = raw.clone();
    let mut sources = vec![];
    if raw.starts_with("---\n") {
        if let Some(end) = raw[4..].find("\n---") {
            let front = parse_front(&raw[4..4 + end]);
            body = raw[4 + end + 4..].trim_start_matches('\n').to_string();
            if let Some(t) = front.get("title") { title = t.clone(); }
            // CE pages often use type:; prefer kind, then type, for Atlas palette fidelity.
            if let Some(k) = front.get("kind").or_else(|| front.get("type")) { kind = k.clone(); }
            if let Some(s) = front.get("stem") { stem = s.clone(); }
            if let Some(s) = front.get("sources").or_else(|| front.get("extracted_from")) { sources = parse_list(s); }
        }
    }
    Some(Page { stem, path: path.to_path_buf(), title, kind, body: body.clone(), links: extract_wikilinks(&body), sources })
}

pub fn list_pages(wiki_dir: &Path) -> Vec<Page> {
    let mut pages = vec![];
    let mut stack = vec![wiki_dir.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(entries) = fs::read_dir(&dir) else { continue };
        for ent in entries.flatten() {
            let p = ent.path();
            if p.is_dir() { stack.push(p); }
            else if p.extension().and_then(|s| s.to_str()) == Some("md") {
                if let Some(page) = parse_page(&p) { pages.push(page); }
            }
        }
    }
    pages.sort_by(|a, b| a.stem.cmp(&b.stem));
    pages
}

pub fn get_page(wiki_dir: &Path, stem: &str) -> Option<Page> {
    list_pages(wiki_dir).into_iter().find(|p| p.stem == stem)
}

pub fn write_page(wiki_dir: &Path, stem: &str, title: &str, body: &str, kind: &str, sources: &[String]) -> Page {
    let _ = fs::create_dir_all(wiki_dir);
    let stem = slugify(if stem.is_empty() { title } else { stem });
    let path = wiki_dir.join(format!("{stem}.md"));
    let mut text = format!("---\nstem: {stem}\ntitle: {title}\nkind: {kind}\n");
    if !sources.is_empty() { text.push_str(&format!("extracted_from: [{}]\n", sources.join(", "))); }
    text.push_str("---\n\n");
    if !body.starts_with('#') { text.push_str(&format!("# {title}\n\n")); }
    text.push_str(body.trim_end());
    text.push('\n');
    let _ = fs::write(&path, text);
    parse_page(&path).unwrap_or(Page { stem, path, title: title.to_string(), kind: kind.to_string(), body: body.to_string(), links: vec![], sources: sources.to_vec() })
}


/// Slice 2: lazy atlas page payload (markdown + minimal HTML).
pub fn markdown_to_html(md: &str) -> String {
    if md.is_empty() { return String::new(); }
    fn esc(s: &str) -> String {
        s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;")
    }
    fn format_inline(raw: &str) -> String {
        // Very small: escape, then wikilinks, bold, italic, code.
        let mut out = String::new();
        let bytes = raw.as_bytes();
        let mut i = 0;
        while i < bytes.len() {
            if i + 1 < bytes.len() && bytes[i] == b'[' && bytes[i + 1] == b'[' {
                if let Some(rel) = raw[i + 2..].find("]]") {
                    let inner = &raw[i + 2..i + 2 + rel];
                    let mut parts = inner.splitn(2, '|');
                    let target = parts.next().unwrap_or("").split('#').next().unwrap_or("").trim();
                    let label = parts.next().unwrap_or(target).trim();
                    let tid = esc(target);
                    out.push_str(&format!(
                        "<a class=\"wikilink\" data-page=\"{tid}\" href=\"#page={tid}\">{}</a>",
                        esc(if label.is_empty() { target } else { label })
                    ));
                    i += 4 + rel;
                    continue;
                }
            }
            if bytes[i] == b'`' {
                if let Some(rel) = raw[i + 1..].find('`') {
                    out.push_str(&format!("<code>{}</code>", esc(&raw[i + 1..i + 1 + rel])));
                    i += 2 + rel;
                    continue;
                }
            }
            if i + 1 < bytes.len() && bytes[i] == b'*' && bytes[i + 1] == b'*' {
                if let Some(rel) = raw[i + 2..].find("**") {
                    out.push_str(&format!("<strong>{}</strong>", esc(&raw[i + 2..i + 2 + rel])));
                    i += 4 + rel;
                    continue;
                }
            }
            // single char escape
            match bytes[i] as char {
                '&' => out.push_str("&amp;"),
                '<' => out.push_str("&lt;"),
                '>' => out.push_str("&gt;"),
                '"' => out.push_str("&quot;"),
                c => out.push(c),
            }
            i += 1;
        }
        out
    }
    let mut out = String::new();
    let mut in_ul = false;
    for line in md.replace("\r\n", "\n").lines() {
        let stripped = line.trim();
        if stripped.is_empty() {
            if in_ul { out.push_str("</ul>"); in_ul = false; }
            continue;
        }
        if stripped.starts_with('#') {
            if in_ul { out.push_str("</ul>"); in_ul = false; }
            let level = stripped.chars().take_while(|c| *c == '#').count().clamp(1, 4);
            let content = stripped[level..].trim();
            out.push_str(&format!("<h{level}>{}</h{level}>", format_inline(content)));
            continue;
        }
        if stripped.starts_with("- ") || stripped.starts_with("* ") {
            if !in_ul { out.push_str("<ul>"); in_ul = true; }
            out.push_str(&format!("<li>{}</li>", format_inline(stripped[2..].trim())));
            continue;
        }
        if in_ul { out.push_str("</ul>"); in_ul = false; }
        out.push_str(&format!("<p>{}</p>", format_inline(stripped)));
    }
    if in_ul { out.push_str("</ul>"); }
    out
}

pub fn page_payload(wiki_dir: &Path, stem: &str) -> Option<serde_json::Value> {
    let page = get_page(wiki_dir, stem)?;
    let sources = page.sources.clone();
    Some(serde_json::json!({
        "id": page.stem,
        "stem": page.stem,
        "title": page.title,
        "type": page.kind,
        "kind": page.kind,
        "path": page.path.to_string_lossy(),
        "properties": { "sources": sources },
        "sources": page.sources,
        "markdown": page.body,
        "body_html": markdown_to_html(&page.body),
    }))
}
