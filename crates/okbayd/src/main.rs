use serde_json::json;
use std::io::{Read, Write};
use std::net::TcpListener;

fn main() {
    let host = std::env::args().position(|a| a == "--host").and_then(|i| std::env::args().nth(i+1)).unwrap_or_else(|| "127.0.0.1".into());
    let port = std::env::args().position(|a| a == "--port").and_then(|i| std::env::args().nth(i+1)).and_then(|s| s.parse().ok()).unwrap_or(8766u16);
    let bind = format!("{host}:{port}");
    let listener = TcpListener::bind(&bind).expect("bind");
    eprintln!("okbayd listening on http://{bind}");
    for stream in listener.incoming() {
        if let Ok(mut s) = stream {
            let mut buf = [0u8; 4096];
            let _ = s.read(&mut buf);
            let req = String::from_utf8_lossy(&buf);
            let path = req.split_whitespace().nth(1).unwrap_or("/");
            let body = if path.starts_with("/health") {
                json!({"ok": true, "daemon": "rust"}).to_string()
            } else if path.starts_with("/api/status") {
                json!({"state": "ready", "pages": 0, "reviews_pending": 0, "daemon": "rust", "api_url": format!("http://127.0.0.1:{port}")}).to_string()
            } else {
                json!({"error": "not found"}).to_string()
            };
            let resp = format!("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}", body.len());
            let _ = s.write_all(resp.as_bytes());
        }
    }
}
