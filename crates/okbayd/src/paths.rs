//! XDG + workspace contract. Mirrors src/okbay/paths.py.

use std::env;
use std::fs;
use std::path::{Path, PathBuf};

pub fn home() -> PathBuf {
    env::var_os("HOME").map(PathBuf::from).unwrap_or_else(|| PathBuf::from("/tmp"))
}
pub fn xdg_state() -> PathBuf {
    env::var_os("XDG_STATE_HOME").map(PathBuf::from).unwrap_or_else(|| home().join(".local/state"))
}
pub fn xdg_config() -> PathBuf {
    env::var_os("XDG_CONFIG_HOME").map(PathBuf::from).unwrap_or_else(|| home().join(".config"))
}
pub fn state_dir() -> PathBuf {
    let p = xdg_state().join("okbay");
    let _ = fs::create_dir_all(&p);
    p
}
pub fn status_path() -> PathBuf { state_dir().join("status.json") }
pub fn default_workspace() -> PathBuf {
    env::var_os("OKBAY_WORKSPACE").map(PathBuf::from).unwrap_or_else(|| home().join("Work/okbay"))
}
pub fn workspace() -> PathBuf {
    let marker = state_dir().join("workspace");
    if let Ok(text) = fs::read_to_string(&marker) {
        let t = text.trim();
        if !t.is_empty() { return PathBuf::from(t); }
    }
    default_workspace()
}
pub fn set_workspace(path: &Path) {
    let _ = fs::write(state_dir().join("workspace"), path.to_string_lossy().as_bytes());
}
pub fn vault(ws: &Path) -> PathBuf { ws.join("vault") }
pub fn wiki(ws: &Path) -> PathBuf { ws.join("wiki") }
pub fn curator(ws: &Path) -> PathBuf { ws.join(".curator") }
pub fn orchestrator(ws: &Path) -> PathBuf { ws.join(".orchestrator") }
pub fn reviews_dir(ws: &Path) -> PathBuf { ws.join(".okbay/reviews") }
pub fn graph_json(ws: &Path) -> PathBuf { curator(ws).join("graph.json") }
pub fn blackboard_path(ws: &Path) -> PathBuf { orchestrator(ws).join("blackboard.json") }
pub fn desks_path(ws: &Path) -> PathBuf { orchestrator(ws).join("desks.json") }
pub fn ensure_workspace(ws: Option<&Path>) -> PathBuf {
    let root = ws.map(|p| p.to_path_buf()).unwrap_or_else(workspace);
    for d in [root.clone(), vault(&root), wiki(&root), curator(&root), orchestrator(&root), reviews_dir(&root), root.join(".okbay")] {
        let _ = fs::create_dir_all(&d);
    }
    set_workspace(&root);
    root
}
