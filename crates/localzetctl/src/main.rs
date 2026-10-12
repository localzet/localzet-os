use localzet_core::{request, Command};
fn main() {
    let cmd = match std::env::args().nth(1).as_deref() {
        Some("ping") => Command::Ping,
        Some("status") => Command::Status,
        Some("version") => Command::Version,
        _ => {
            eprintln!("Usage: localzetctl ping|status|version");
            std::process::exit(2)
        }
    };
    match request(cmd) {
        Ok(reply) => println!("{reply}"),
        Err(err) => {
            eprintln!("localzetctl: {err}");
            std::process::exit(1)
        }
    }
}
