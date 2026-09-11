//! OKBay warm daemon. Same HTTP contract as `python -m okbay serve`.
mod atlas_ce;
mod desks;
mod graph;
mod http;
mod ingest;
mod locate;
mod paths;
mod reviews;
mod status;
mod store;
mod theme;
mod wiki;

fn main() {
    let mut host = "127.0.0.1".to_string();
    let mut port = 8766u16;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--host" => host = args.next().unwrap_or(host),
            "--port" => port = args.next().and_then(|s| s.parse().ok()).unwrap_or(port),
            _ => {}
        }
    }
    if let Err(e) = http::serve(&host, port) {
        eprintln!("okbayd: {e}");
        std::process::exit(1);
    }
}
