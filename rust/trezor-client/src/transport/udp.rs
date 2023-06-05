use super::{
    error::Error,
    protocol::{Link, Protocol, ProtocolV1},
    AvailableDeviceTransport, ProtoMessage, Transport,
};
use crate::{AvailableDevice, Model};
use std::{fmt, net::UdpSocket, result::Result, time::Duration};

// A collection of constants related to the Emulator Ports.
mod constants {
    pub const DEFAULT_HOST: &str = "127.0.0.1";
    pub const DEFAULT_PORT: &str = "21324";
    pub const DEFAULT_DEBUG_PORT: &str = "21325";
    pub const LOCAL_LISTENER: &str = "127.0.0.1:0";
}

use constants::{DEFAULT_DEBUG_PORT, DEFAULT_HOST, DEFAULT_PORT, LOCAL_LISTENER};

/// The chunk size for the serial protocol.
const CHUNK_SIZE: usize = 64;

const READ_TIMEOUT_MS: u64 = 100000;
const WRITE_TIMEOUT_MS: u64 = 100000;

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
    pub socket: UdpSocket,
    pub device: (String, String),
}
// No need to implement drop as every member is owned

impl Link for UdpLink {
    fn write_chunk(&mut self, chunk: Vec<u8>) -> Result<(), Error> {
        debug_assert_eq!(CHUNK_SIZE, chunk.len());
        let timeout = Duration::from_millis(WRITE_TIMEOUT_MS);
        self.socket.set_write_timeout(Some(timeout))?;
        if let Err(e) = self.socket.send(&chunk) {
            return Err(e.into())
        }
        Ok(())
    }

    fn read_chunk(&mut self) -> Result<Vec<u8>, Error> {
        let mut chunk = vec![0; CHUNK_SIZE];
        let timeout = Duration::from_millis(READ_TIMEOUT_MS);
        self.socket.set_read_timeout(Some(timeout))?;

        let n = self.socket.recv(&mut chunk)?;
        if n == CHUNK_SIZE {
            Ok(chunk)
        } else {
            Err(Error::DeviceReadTimeout)
        }
    }
}

impl UdpLink {
    pub fn open(path: &str) -> Result<UdpLink, Error> {
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
        self.socket.send("PINGPING".as_bytes())?;
        let size = self.socket.recv(&mut resp)?;
        Ok(&resp[..size] == "PONGPONG".as_bytes())
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
        let link = UdpLink::open(&path)?;
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
