use serde_json::{json, Map, Value};
use std::fs;
use std::path::PathBuf;

fn home() -> PathBuf {
    std::env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("/tmp"))
}

fn colors_toml_path() -> Option<PathBuf> {
    let state = std::env::var_os("XDG_STATE_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| home().join(".local/state"));
    let cands = [
        state.join("omarchy/current/theme/colors.toml"),
        home().join(".config/omarchy/current/theme/colors.toml"),
        home().join(".config/omarchy/themes/switchbay/colors.toml"),
    ];
    cands.into_iter().find(|p| p.is_file())
}

fn parse_toml_colors(text: &str) -> std::collections::BTreeMap<String, String> {
    let mut out = std::collections::BTreeMap::new();
    for raw in text.lines() {
        let line = raw.split('#').next().unwrap_or("").trim();
        if let Some((k, v)) = line.split_once('=') {
            let val = v.trim().trim_matches('"').trim_matches('\'').to_string();
            // Empty values must not blank Switchbay fallbacks (CE Atlas palette).
            if !val.is_empty() {
                out.insert(k.trim().to_string(), val);
            }
        }
    }
    out
}

fn color(
    colors: &std::collections::BTreeMap<String, String>,
    keys: &[&str],
    fallback: &str,
) -> String {
    for k in keys {
        if let Some(v) = colors.get(*k) {
            if !v.is_empty() {
                return v.clone();
            }
        }
    }
    fallback.to_string()
}

/// Full Switchbay CE type palette (parity with Python theme.SWITCHBAY_TYPE).
fn type_palette(colors: &std::collections::BTreeMap<String, String>) -> Map<String, Value> {
    let pairs: &[(&str, &[&str], &str)] = &[
        ("project", &["type_project", "type-project", "bright_blue"], "#4d1ae8"),
        ("projects", &["type_project", "type-project", "bright_blue"], "#4d1ae8"),
        ("analysis", &["type_analysis", "type-analysis", "blue"], "#1d6996"),
        ("analyses", &["type_analysis", "type-analysis", "blue"], "#1d6996"),
        ("concept", &["type_concept", "type-concept", "cyan"], "#38a6a5"),
        ("concepts", &["type_concept", "type-concept", "cyan"], "#38a6a5"),
        ("entity", &["type_entity", "type-entity", "green"], "#0f8554"),
        ("entities", &["type_entity", "type-entity", "green"], "#0f8554"),
        ("evidence", &["type_evidence", "type-evidence", "bright_green"], "#73af48"),
        ("fact", &["type_fact", "type-fact", "yellow"], "#edad08"),
        ("facts", &["type_fact", "type-fact", "yellow"], "#edad08"),
        ("figure", &["type_figure", "type-figure", "orange"], "#e17c05"),
        ("figures", &["type_figure", "type-figure", "orange"], "#e17c05"),
        ("table", &["type_table", "type-table", "red"], "#cc503e"),
        ("tables", &["type_table", "type-table", "red"], "#cc503e"),
        ("source", &["type_source", "type-source", "magenta"], "#94346e"),
        ("sources", &["type_source", "type-source", "magenta"], "#94346e"),
        ("note", &["type_note", "type-note", "brown"], "#6f4070"),
        ("notes", &["type_note", "type-note", "brown"], "#6f4070"),
        ("todo", &["type_todo", "type-todo", "bright_magenta"], "#9656a2"),
        ("todo-list", &["type_todo", "type-todo-list", "bright_magenta"], "#9656a2"),
        ("hub", &["type_hub", "type-hub", "accent"], "#6be8b3"),
        ("unclassified", &["type_unclassified", "bright_foreground"], "#ffffff"),
        ("missing", &["type_missing", "muted"], "#5a6068"),
        ("default", &["dark_foreground"], "#9aa0a8"),
    ];
    let mut kinds = Map::new();
    for (name, keys, fb) in pairs {
        kinds.insert((*name).to_string(), json!(color(colors, keys, fb)));
    }
    kinds
}

pub fn atlas_theme() -> Value {
    let mut colors = std::collections::BTreeMap::from([
        ("accent".into(), "#6be8b3".into()),
        ("background".into(), "#0f1115".into()),
        ("foreground".into(), "#e6e8eb".into()),
        ("muted".into(), "#343942".into()),
        ("dark_foreground".into(), "#5a6068".into()),
        ("light_foreground".into(), "#9aa0a8".into()),
        ("bright_foreground".into(), "#f4f6f8".into()),
        ("selection".into(), "#1f242c".into()),
        ("dark_background".into(), "#0c0e12".into()),
        ("lighter_background".into(), "#161a21".into()),
        ("darker_background".into(), "#08090c".into()),
        ("red".into(), "#cc503e".into()),
        ("yellow".into(), "#edad08".into()),
        ("orange".into(), "#e17c05".into()),
        ("green".into(), "#0f8554".into()),
        ("cyan".into(), "#38a6a5".into()),
        ("blue".into(), "#1d6996".into()),
        ("magenta".into(), "#94346e".into()),
        ("brown".into(), "#6f4070".into()),
        ("bright_red".into(), "#e17c05".into()),
        ("bright_yellow".into(), "#edad08".into()),
        ("bright_green".into(), "#73af48".into()),
        ("bright_cyan".into(), "#6be8b3".into()),
        ("bright_blue".into(), "#4d1ae8".into()),
        ("bright_magenta".into(), "#9656a2".into()),
    ]);
    let source = colors_toml_path();
    if let Some(p) = &source {
        if let Ok(text) = fs::read_to_string(p) {
            colors.extend(parse_toml_colors(&text));
        }
    }
    let chrome = json!({
        "accent": color(&colors, &["accent"], "#6be8b3"),
        "background": color(&colors, &["background"], "#0f1115"),
        "foreground": color(&colors, &["foreground"], "#e6e8eb"),
        "muted": color(&colors, &["muted"], "#343942"),
        "dark_foreground": color(&colors, &["dark_foreground"], "#5a6068"),
        "light_foreground": color(&colors, &["light_foreground"], "#9aa0a8"),
        "selection": color(&colors, &["selection"], "#1f242c"),
        "dark_background": color(&colors, &["dark_background"], "#0c0e12"),
        "lighter_background": color(&colors, &["lighter_background"], "#161a21"),
        "darker_background": color(&colors, &["darker_background"], "#08090c"),
    });
    let kinds = Value::Object(type_palette(&colors));
    let mut css = serde_json::Map::new();
    if let Some(obj) = chrome.as_object() {
        for (k, v) in obj {
            if let Some(s) = v.as_str() {
                css.insert(format!("--{}", k.replace('_', "-")), json!(s));
            }
        }
    }
    css.insert("--accent".into(), chrome["accent"].clone());
    json!({
        "name": "omarchy-or-switchbay",
        "source": source.map(|p| p.display().to_string()).unwrap_or_default(),
        "chrome": chrome,
        "kinds": kinds,
        "types": kinds,
        "css": css,
        "theme": "omarchy",
        "mode": colors.get("mode").cloned().unwrap_or_else(|| "dark".into()),
    })
}
