//! Localzet OS daemon. Local read-only API over a Unix domain socket.
use localzet_core::{Command, PROTOCOL_VERSION, SOCKET_PATH};
use std::fs;
use std::io::{self, BufRead, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::Path;

fn serve(mut stream: UnixStream) -> io::Result<()> {
    let mut input = String::new();
    {
        let mut reader = io::BufReader::new(&stream);
        reader.read_line(&mut input)?;
    }
    let answer = match Command::parse(&input) {
        Some(Command::Ping) => "PONG".to_string(),
        Some(Command::Version) => format!("localzetd/0.1.0 protocol/{PROTOCOL_VERSION}"),
        Some(Command::Status) => {
            let uptime = fs::read_to_string("/proc/uptime").unwrap_or_default();
            let seconds = uptime.split_whitespace().next().unwrap_or("unknown");
            format!("OK uptime_seconds={seconds}")
        }
        None => "ERR unknown_command".to_string(),
    };
    stream.write_all(format!("{answer}\n").as_bytes())?;
    stream.flush()
}

fn main() -> io::Result<()> {
    let socket = Path::new(SOCKET_PATH);
    let parent = socket.parent().expect("socket must have parent");
    fs::create_dir_all(parent)?;
    // systemd RuntimeDirectory removes stale sockets at service shutdown.
    if socket.exists() {
        fs::remove_file(socket)?;
    }
    let listener = UnixListener::bind(socket)?;
    fs::set_permissions(socket, fs::Permissions::from_mode(0o666))?;
    eprintln!("localzetd listening on {SOCKET_PATH}");
    for connection in listener.incoming() {
        match connection {
            Ok(stream) => {
                if let Err(err) = serve(stream) {
                    eprintln!("client error: {err}");
                }
            }
            Err(err) => eprintln!("accept error: {err}"),
        }
    }
    Ok(())
}
