use super::{
    error::Error,
    protocol::{Link, Protocol, ProtocolV1},
    AvailableDeviceTransport, ProtoMessage, Transport,
};
use crate::{AvailableDevice, Model};
use std::{
    fmt,
    io::ErrorKind,
    net::UdpSocket,
    result::Result,
    time::{Duration, Instant},
};

// A collection of constants related to the Emulator Ports.
mod constants {
    pub(crate) const DEFAULT_HOST: &str = "127.0.0.1";
    pub(crate) const DEFAULT_PORT: &str = "21324";
    pub(crate) const DEFAULT_DEBUG_PORT: &str = "21325";
    pub(crate) const LOCAL_LISTENER: &str = "127.0.0.1:0";
}

use constants::{DEFAULT_DEBUG_PORT, DEFAULT_HOST, DEFAULT_PORT, LOCAL_LISTENER};

/// The chunk size for the serial protocol.
const CHUNK_SIZE: usize = 64;

/// Total time to wait for a single chunk before giving up. Deliberately
/// generous, because the emulator legitimately blocks on the user. The point
/// is only that the wait is now *finite*: a wedged or vanished peer surfaces a
/// [`Error::DeviceReadTimeout`] instead of blocking forever, which the
/// previous value of `None` ("block indefinitely") allowed.
const READ_TIMEOUT: Duration = Duration::from_secs(600);
/// Poll slice within [`READ_TIMEOUT`]; we retry the blocking `recv` until the
/// deadline is reached.
const READ_POLL: Duration = Duration::from_millis(100);
const WRITE_TIMEOUT: Duration = Duration::from_secs(1);
/// Per-read timeout while discarding stale chunks on connect.
const DRAIN_TIMEOUT: Duration = Duration::from_millis(10);
/// Upper bound on datagrams discarded while draining, so a peer that keeps
/// sending can never hold the connect path open (worst case
/// `DRAIN_MAX_CHUNKS * DRAIN_TIMEOUT`). A real stale buffer is a few chunks.
const DRAIN_MAX_CHUNKS: usize = 1024;
/// Timeout for the discovery probe, so scanning for an emulator that never
/// answers cannot hang the caller.
const PROBE_TIMEOUT: Duration = Duration::from_millis(500);

/// An available transport for connecting with a device.
#[derive(Debug)]
pub struct AvailableUdpTransport {
    pub host: String,
    pub port: String,
}

impl fmt::Display for AvailableUdpTransport {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "udp:{}:{}", self.host, self.port)
    }
}

/// An actual serial HID USB link to a device over which bytes can be sent.
struct UdpLink {
    socket: UdpSocket,
    device: (String, String),
}
// No need to implement drop as every member is owned

impl Link for UdpLink {
    fn write_chunk(&mut self, chunk: Vec<u8>) -> Result<(), Error> {
        debug_assert_eq!(CHUNK_SIZE, chunk.len());
        self.socket.set_write_timeout(Some(WRITE_TIMEOUT))?;
        if let Err(e) = self.socket.send(&chunk) {
            return Err(e.into());
        }
        Ok(())
    }

    fn read_chunk(&mut self) -> Result<Vec<u8>, Error> {
        self.read_chunk_until(Instant::now() + READ_TIMEOUT)
    }
}

impl UdpLink {
    fn open(path: &str) -> Result<UdpLink, Error> {
        let mut parts = path.split(':');
        let link = Self {
            socket: UdpSocket::bind(LOCAL_LISTENER)?,
            device: (
                parts.next().expect("Incorrect Path").to_owned(),
                parts.next().expect("Incorrect Path").to_owned(),
            ),
        };
        link.socket.connect(path)?;
        Ok(link)
    }

    // Ping the port and compare against expected response
    fn ping(&self) -> Result<bool, Error> {
        let mut resp = [0; CHUNK_SIZE];
        // Bound the probe so discovery cannot hang on a port that never replies.
        self.socket.set_read_timeout(Some(PROBE_TIMEOUT))?;
        self.socket.send("PINGPING".as_bytes())?;
        match self.socket.recv(&mut resp) {
            Ok(size) => Ok(&resp[..size] == "PONGPONG".as_bytes()),
            // No emulator answered within the probe window, or the socket
            // reported that nothing is listening. That just means "not here",
            // not an error worth propagating up through discovery.
            Err(e)
                if e.kind() == ErrorKind::WouldBlock
                    || e.kind() == ErrorKind::TimedOut
                    || e.kind() == ErrorKind::ConnectionRefused =>
            {
                Ok(false)
            }
            Err(e) => Err(e.into()),
        }
    }

    /// Read one chunk, polling in [`READ_POLL`] slices until `deadline`, after
    /// which [`Error::DeviceReadTimeout`] is returned instead of blocking
    /// forever on a peer that has gone silent.
    fn read_chunk_until(&mut self, deadline: Instant) -> Result<Vec<u8>, Error> {
        let mut chunk = vec![0; CHUNK_SIZE];
        loop {
            let now = Instant::now();
            if now >= deadline {
                return Err(Error::DeviceReadTimeout);
            }
            // Floor at 1 ms to match the webusb path and keep the per-poll
            // timeout safely non-zero.
            let poll = READ_POLL.min(deadline - now).max(Duration::from_millis(1));
            self.socket.set_read_timeout(Some(poll))?;
            match self.socket.recv(&mut chunk) {
                Ok(n) if n == CHUNK_SIZE => return Ok(chunk),
                Ok(n) => return Err(Error::UnexpectedChunkSizeFromDevice(n)),
                Err(e) if e.kind() == ErrorKind::WouldBlock || e.kind() == ErrorKind::TimedOut => {
                    continue
                }
                Err(e) => return Err(e.into()),
            }
        }
    }

    /// Discard any stale datagrams left buffered from a previous, interrupted
    /// session. Without this, the first response can be paired with a leftover
    /// message and the link stays desynchronised for the rest of its life.
    fn drain(&mut self) {
        let mut chunk = vec![0; CHUNK_SIZE];
        if self.socket.set_read_timeout(Some(DRAIN_TIMEOUT)).is_err() {
            return;
        }
        for _ in 0..DRAIN_MAX_CHUNKS {
            if self.socket.recv(&mut chunk).is_err() {
                break;
            }
        }
    }
}

/// An implementation of the Transport interface for UDP devices.
pub struct UdpTransport {
    protocol: ProtocolV1<UdpLink>,
}

impl UdpTransport {
    pub fn find_devices(debug: bool, path: Option<&str>) -> Result<Vec<AvailableDevice>, Error> {
        let mut devices = Vec::new();
        let mut dest = String::new();
        match path {
            Some(p) => dest = p.to_owned(),
            None => {
                dest.push_str(DEFAULT_HOST);
                dest.push(':');
                dest.push_str(if debug { DEFAULT_DEBUG_PORT } else { DEFAULT_PORT });
            }
        };
        let link = UdpLink::open(&dest)?;
        if link.ping()? {
            devices.push(AvailableDevice {
                model: Model::TrezorEmulator,
                debug,
                transport: AvailableDeviceTransport::Udp(AvailableUdpTransport {
                    host: link.device.0,
                    port: link.device.1,
                }),
            });
        }
        Ok(devices)
    }

    /// Connect to a device over the UDP transport.
    pub fn connect(device: &AvailableDevice) -> Result<Box<dyn Transport>, Error> {
        let transport = match device.transport {
            AvailableDeviceTransport::Udp(ref t) => t,
            _ => panic!("passed wrong AvailableDevice in UdpTransport::connect"),
        };
        let mut path = String::new();
        path.push_str(&transport.host);
        path.push(':');
        path.push_str(&transport.port);
        let mut link = UdpLink::open(&path)?;
        // Drop any stale datagrams before the first real exchange.
        link.drain();
        Ok(Box::new(UdpTransport { protocol: ProtocolV1 { link } }))
    }
}

impl super::Transport for UdpTransport {
    fn session_begin(&mut self) -> Result<(), Error> {
        self.protocol.session_begin()
    }
    fn session_end(&mut self) -> Result<(), Error> {
        self.protocol.session_end()
    }

    fn write_message(&mut self, message: ProtoMessage) -> Result<(), Error> {
        self.protocol.write(message)
    }
    fn read_message(&mut self) -> Result<ProtoMessage, Error> {
        self.protocol.read()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Bind a loopback UDP socket, returning `None` (so the test is skipped)
    /// if the sandbox forbids it.
    fn loopback() -> Option<UdpSocket> {
        UdpSocket::bind("127.0.0.1:0").ok()
    }

    fn link_connected_to(addr: &str) -> Option<UdpLink> {
        let socket = loopback()?;
        socket.connect(addr).ok()?;
        Some(UdpLink { socket, device: ("127.0.0.1".to_owned(), "0".to_owned()) })
    }

    #[test]
    fn read_chunk_times_out_against_a_silent_peer() {
        let Some(peer) = loopback() else {
            eprintln!("skipping: no loopback UDP available");
            return;
        };
        let addr = peer.local_addr().unwrap().to_string();
        let mut link = link_connected_to(&addr).unwrap();

        let deadline = Instant::now() + Duration::from_millis(150);
        let err = link.read_chunk_until(deadline).unwrap_err();
        assert!(matches!(err, Error::DeviceReadTimeout), "unexpected error: {err:?}");
    }

    #[test]
    fn drain_discards_stale_chunks() {
        let Some(peer) = loopback() else {
            eprintln!("skipping: no loopback UDP available");
            return;
        };
        let peer_addr = peer.local_addr().unwrap().to_string();
        let mut link = link_connected_to(&peer_addr).unwrap();
        let client_addr = link.socket.local_addr().unwrap();

        // The peer leaves a stale chunk buffered for the client.
        peer.send_to(&[0xAA; CHUNK_SIZE], client_addr).unwrap();
        std::thread::sleep(Duration::from_millis(50));

        link.drain();

        // Nothing is left to read, so the watchdog fires rather than handing
        // back the stale bytes that drain was supposed to discard.
        let deadline = Instant::now() + Duration::from_millis(150);
        assert!(matches!(
            link.read_chunk_until(deadline).unwrap_err(),
            Error::DeviceReadTimeout
        ));
    }

    #[test]
    fn read_chunk_returns_a_full_chunk() {
        let Some(peer) = loopback() else {
            eprintln!("skipping: no loopback UDP available");
            return;
        };
        let peer_addr = peer.local_addr().unwrap().to_string();
        let mut link = link_connected_to(&peer_addr).unwrap();
        let client_addr = link.socket.local_addr().unwrap();

        peer.send_to(&[0x7E; CHUNK_SIZE], client_addr).unwrap();

        let deadline = Instant::now() + Duration::from_secs(2);
        let chunk = link.read_chunk_until(deadline).unwrap();
        assert_eq!(chunk.len(), CHUNK_SIZE);
        assert!(chunk.iter().all(|&b| b == 0x7E));
    }
}
