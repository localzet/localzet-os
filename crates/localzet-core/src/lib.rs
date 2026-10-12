//! Shared protocol for the Localzet OS system daemon.
use std::io::{self, BufRead, Write};
use std::os::unix::net::UnixStream;

pub const SOCKET_PATH: &str = "/run/localzet-os/system.sock";
pub const PROTOCOL_VERSION: &str = "1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Command {
    Ping,
    Status,
    Version,
}

impl Command {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Ping => "PING",
            Self::Status => "STATUS",
            Self::Version => "VERSION",
        }
    }
    pub fn parse(input: &str) -> Option<Self> {
        match input.trim() {
            "PING" => Some(Self::Ping),
            "STATUS" => Some(Self::Status),
            "VERSION" => Some(Self::Version),
            _ => None,
        }
    }
}

pub fn request(command: Command) -> io::Result<String> {
    let mut stream = UnixStream::connect(SOCKET_PATH)?;
    stream.write_all(format!("{}\n", command.as_str()).as_bytes())?;
    stream.flush()?;
    let mut answer = String::new();
    let mut reader = io::BufReader::new(stream);
    if reader.read_line(&mut answer)? == 0 {
        return Err(io::Error::new(
            io::ErrorKind::UnexpectedEof,
            "daemon closed connection",
        ));
    }
    Ok(answer.trim_end().to_owned())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn command_roundtrip() {
        for cmd in [Command::Ping, Command::Status, Command::Version] {
            assert_eq!(Command::parse(cmd.as_str()), Some(cmd));
        }
        assert_eq!(Command::parse("REBOOT"), None);
    }
}
