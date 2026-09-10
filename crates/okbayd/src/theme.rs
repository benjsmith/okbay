use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;

fn home() -> PathBuf { std::env::var_os("HOME").map(PathBuf::from).unwrap_or_else(|| PathBuf::from("/tmp")) }

fn colors_toml_path() -> Option<PathBuf> {
    let state = std::env::var_os("XDG_STATE_HOME").map(PathBuf::from).unwrap_or_else(|| home().join(".local/state"));
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
            out.insert(k.trim().to_string(), v.trim().trim_matches('"').trim_matches('\'').to_string());
        }
    }
    out
}

pub fn atlas_theme() -> Value {
    let mut colors = std::collections::BTreeMap::from([
        ("accent".into(), "#6be8b3".into()),
        ("background".into(), "#0f1115".into()),
        ("foreground".into(), "#e6e8eb".into()),
        ("muted".into(), "#343942".into()),
        ("dark_foreground".into(), "#5a6068".into()),
        ("light_foreground".into(), "#9aa0a8".into()),
        ("selection".into(), "#1f242c".into()),
        ("dark_background".into(), "#0c0e12".into()),
        ("lighter_background".into(), "#161a21".into()),
        ("darker_background".into(), "#08090c".into()),
        ("type_fact".into(), "#edad08".into()),
        ("type_project".into(), "#4d1ae8".into()),
        ("type_source".into(), "#94346e".into()),
        ("type_hub".into(), "#6be8b3".into()),
    ]);
    let source = colors_toml_path();
    if let Some(p) = &source {
        if let Ok(text) = fs::read_to_string(p) {
            colors.extend(parse_toml_colors(&text));
        }
    }
    let chrome = json!({
        "accent": colors.get("accent").cloned().unwrap_or_else(|| "#6be8b3".into()),
        "background": colors.get("background").cloned().unwrap_or_else(|| "#0f1115".into()),
        "foreground": colors.get("foreground").cloned().unwrap_or_else(|| "#e6e8eb".into()),
        "muted": colors.get("muted").cloned().unwrap_or_else(|| "#343942".into()),
        "dark_foreground": colors.get("dark_foreground").cloned().unwrap_or_else(|| "#5a6068".into()),
        "light_foreground": colors.get("light_foreground").cloned().unwrap_or_else(|| "#9aa0a8".into()),
        "selection": colors.get("selection").cloned().unwrap_or_else(|| "#1f242c".into()),
        "dark_background": colors.get("dark_background").cloned().unwrap_or_else(|| "#0c0e12".into()),
        "lighter_background": colors.get("lighter_background").cloned().unwrap_or_else(|| "#161a21".into()),
        "darker_background": colors.get("darker_background").cloned().unwrap_or_else(|| "#08090c".into()),
    });
    let kinds = json!({
        "fact": colors.get("type_fact").or_else(|| colors.get("yellow")).cloned().unwrap_or_else(|| "#edad08".into()),
        "project": colors.get("type_project").or_else(|| colors.get("bright_blue")).cloned().unwrap_or_else(|| "#4d1ae8".into()),
        "source": colors.get("type_source").or_else(|| colors.get("magenta")).cloned().unwrap_or_else(|| "#94346e".into()),
        "hub": colors.get("type_hub").or_else(|| colors.get("accent")).cloned().unwrap_or_else(|| "#6be8b3".into()),
        "note": colors.get("type_note").or_else(|| colors.get("brown")).cloned().unwrap_or_else(|| "#6f4070".into()),
        "concept": colors.get("type_concept").or_else(|| colors.get("cyan")).cloned().unwrap_or_else(|| "#38a6a5".into()),
        "default": "#bbbbbb",
    });
    let mut css = serde_json::Map::new();
    if let Some(obj) = chrome.as_object() {
        for (k, v) in obj {
            if let Some(s) = v.as_str() { css.insert(format!("--{}", k.replace('_', "-")), json!(s)); }
        }
    }
    css.insert("--accent".into(), chrome["accent"].clone());
    json!({"name": "omarchy-or-switchbay", "source": source.map(|p| p.display().to_string()).unwrap_or_default(), "chrome": chrome, "kinds": kinds, "types": kinds, "css": css, "theme": "omarchy"})
}
