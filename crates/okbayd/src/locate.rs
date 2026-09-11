use crate::paths;
use crate::wiki::get_page;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::process::Command;

fn which(bin: &str) -> bool {
    std::env::var_os("PATH")
        .map(|paths| {
            std::env::split_paths(&paths).any(|dir| {
                let p = dir.join(bin);
                p.is_file()
            })
        })
        .unwrap_or(false)
}

fn spawn(cmd: &[String]) -> bool {
    if cmd.is_empty() {
        return false;
    }
    Command::new(&cmd[0])
        .args(&cmd[1..])
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
        .is_ok()
}

/// Ordered Omarchy Nautilus → xdg-open launch candidates for Reveal.
fn reveal_candidates(target: &Path) -> Vec<Vec<String>> {
    let parent = target.parent().filter(|p| p.exists());
    let is_file = target.is_file();
    let is_dir = target.is_dir();
    let open_dir: Option<&Path> = if is_dir {
        Some(target)
    } else {
        parent
    };
    let Some(open_dir) = open_dir else {
        return vec![];
    };

    let has_nautilus = which("nautilus");
    let has_uwsm = which("uwsm-app");
    let has_xdg = which("xdg-open");
    let mut cmds: Vec<Vec<String>> = Vec::new();

    let push = |cmds: &mut Vec<Vec<String>>, parts: &[&str]| {
        cmds.push(parts.iter().map(|s| (*s).to_string()).collect());
    };

    if has_nautilus {
        if is_file {
            let path = target.to_string_lossy();
            if has_uwsm {
                push(
                    &mut cmds,
                    &["uwsm-app", "--", "nautilus", "--select", path.as_ref()],
                );
            }
            push(&mut cmds, &["nautilus", "--select", path.as_ref()]);
        }
        let dir = open_dir.to_string_lossy();
        if has_uwsm {
            push(
                &mut cmds,
                &[
                    "uwsm-app",
                    "--",
                    "nautilus",
                    "--new-window",
                    dir.as_ref(),
                ],
            );
        }
        push(&mut cmds, &["nautilus", "--new-window", dir.as_ref()]);
    }

    if has_xdg {
        let dir = open_dir.to_string_lossy();
        push(&mut cmds, &["xdg-open", dir.as_ref()]);
    }

    cmds
}

fn reveal_path(target: &Path) -> (Option<Vec<String>>, Option<String>) {
    let candidates = reveal_candidates(target);
    if candidates.is_empty() {
        return (None, Some("no file manager / path missing".into()));
    }
    let mut last_err = "file manager launch failed".to_string();
    for cmd in candidates {
        if spawn(&cmd) {
            return (Some(cmd), None);
        }
        last_err = format!("failed to spawn {}", cmd.join(" "));
    }
    (None, Some(last_err))
}

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
    if which("hyprctl") {
        out["hypr"] = json!("available");
    }
    if reveal {
        let (cmd, err) = reveal_path(PathBuf::from(&target).as_path());
        if let Some(cmd) = cmd {
            let joined = cmd.join(" ");
            let via = if joined.contains("nautilus") {
                "nautilus"
            } else if joined.contains("xdg-open") {
                "xdg-open"
            } else {
                Path::new(cmd.first().map(|s| s.as_str()).unwrap_or("unknown"))
                    .file_name()
                    .and_then(|s| s.to_str())
                    .unwrap_or("unknown")
            };
            out["revealed"] = json!(cmd);
            out["reveal_via"] = json!(via);
        } else if let Some(e) = err {
            out["reveal_error"] = json!(e);
        } else {
            out["reveal_error"] = json!("no file manager / path missing");
        }
    }
    out
}
