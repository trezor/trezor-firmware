use crate::{
    transport::{
        derive_model,
        error::Error,
        protocol::{Link, Protocol, ProtocolV1},
        AvailableDeviceTransport, ProtoMessage, Transport,
    },
    AvailableDevice,
};
use rusb::*;
use std::{
    fmt,
    result::Result,
    time::{Duration, Instant},
};

// A collection of constants related to the WebUsb protocol.
mod constants {
    pub(crate) const CONFIG_ID: u8 = 0;
    pub(crate) const INTERFACE_DESCRIPTOR: u8 = 0;
    pub(crate) const LIBUSB_CLASS_VENDOR_SPEC: u8 = 0xff;

    pub(crate) const INTERFACE: u8 = 0;
    pub(crate) const INTERFACE_DEBUG: u8 = 1;
    pub(crate) const ENDPOINT: u8 = 1;
    pub(crate) const ENDPOINT_DEBUG: u8 = 2;
    pub(crate) const READ_ENDPOINT_MASK: u8 = 0x80;
}

/// The chunk size for the serial protocol.
const CHUNK_SIZE: usize = 64;

/// Total time to wait for a single chunk before giving up. Deliberately
/// generous, because the device legitimately blocks on the user (a button
/// press or PIN entry can take as long as the user needs). The point is only
/// that the wait is now *finite*: a vanished or wedged device surfaces a
/// [`Error::DeviceReadTimeout`] instead of blocking forever, which the
/// previous value of `0` ("wait indefinitely") allowed.
const READ_TIMEOUT: Duration = Duration::from_secs(600);
/// Poll slice within [`READ_TIMEOUT`]: a libusb interrupt read returns
/// `Timeout` after each slice with no data, and we retry until the deadline.
const READ_POLL: Duration = Duration::from_millis(100);
const WRITE_TIMEOUT: Duration = Duration::from_secs(1);
/// Per-read timeout while discarding stale chunks on connect.
const DRAIN_TIMEOUT: Duration = Duration::from_millis(10);
/// Upper bound on chunks discarded while draining, so a device that keeps
/// producing data can never hold the connect path open (worst case
/// `DRAIN_MAX_CHUNKS * DRAIN_TIMEOUT`). A real stale buffer is a few chunks.
const DRAIN_MAX_CHUNKS: usize = 1024;

/// An available transport for connecting with a device.
#[derive(Debug)]
pub struct AvailableWebUsbTransport {
    pub bus: u8,
    pub address: u8,
}

impl fmt::Display for AvailableWebUsbTransport {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "WebUSB ({}:{})", self.bus, self.address)
    }
}

/// An actual serial USB link to a device over which bytes can be sent.
pub struct WebUsbLink {
    handle: DeviceHandle<GlobalContext>,
    endpoint: u8,
}

impl Link for WebUsbLink {
    fn write_chunk(&mut self, chunk: Vec<u8>) -> Result<(), Error> {
        debug_assert_eq!(CHUNK_SIZE, chunk.len());
        if let Err(e) = self.handle.write_interrupt(self.endpoint, &chunk, WRITE_TIMEOUT) {
            return Err(e.into());
        }
        Ok(())
    }

    fn read_chunk(&mut self) -> Result<Vec<u8>, Error> {
        self.read_chunk_until(Instant::now() + READ_TIMEOUT)
    }
}

impl WebUsbLink {
    /// Read one chunk, polling in [`READ_POLL`] slices until `deadline`, after
    /// which [`Error::DeviceReadTimeout`] is returned instead of blocking
    /// forever on a device that has gone away.
    fn read_chunk_until(&mut self, deadline: Instant) -> Result<Vec<u8>, Error> {
        let endpoint = constants::READ_ENDPOINT_MASK | self.endpoint;
        let mut chunk = vec![0; CHUNK_SIZE];
        loop {
            let now = Instant::now();
            if now >= deadline {
                return Err(Error::DeviceReadTimeout);
            }
            // Floor at 1 ms: rusb converts the timeout to whole milliseconds
            // (`as_millis() as c_uint`), so a sub-millisecond value truncates
            // to 0, which libusb treats as "block indefinitely" -- the exact
            // hang this loop exists to prevent. Overshooting the deadline by up
            // to one poll slice is harmless; the next iteration catches it.
            let poll = READ_POLL.min(deadline - now).max(Duration::from_millis(1));
            match self.handle.read_interrupt(endpoint, &mut chunk, poll) {
                Ok(n) if n == CHUNK_SIZE => return Ok(chunk),
                Ok(n) => return Err(Error::UnexpectedChunkSizeFromDevice(n)),
                Err(rusb::Error::Timeout) => continue,
                Err(e) => return Err(e.into()),
            }
        }
    }

    /// Discard any stale chunks left buffered from a previous, interrupted
    /// session. Without this, the first response can be paired with a leftover
    /// message and the link stays desynchronised for the rest of its life.
    fn drain(&mut self) {
        let endpoint = constants::READ_ENDPOINT_MASK | self.endpoint;
        let mut chunk = vec![0; CHUNK_SIZE];
        for _ in 0..DRAIN_MAX_CHUNKS {
            if self.handle.read_interrupt(endpoint, &mut chunk, DRAIN_TIMEOUT).is_err() {
                break;
            }
        }
    }
}

/// An implementation of the Transport interface for WebUSB devices.
pub struct WebUsbTransport {
    protocol: ProtocolV1<WebUsbLink>,
}

impl WebUsbTransport {
    pub fn find_devices(debug: bool) -> Result<Vec<AvailableDevice>, Error> {
        let mut devices = Vec::new();

        for dev in rusb::devices().unwrap().iter() {
            let desc = dev.device_descriptor()?;
            let dev_id = (desc.vendor_id(), desc.product_id());

            let model = match derive_model(dev_id) {
                Some(m) => m,
                None => continue,
            };

            // Check something with interface class code like python-trezor does.
            let class_code = dev
                .config_descriptor(constants::CONFIG_ID)?
                .interfaces()
                .find(|i| i.number() == constants::INTERFACE)
                .ok_or(rusb::Error::Other)?
                .descriptors()
                .find(|d| d.setting_number() == constants::INTERFACE_DESCRIPTOR)
                .ok_or(rusb::Error::Other)?
                .class_code();
            if class_code != constants::LIBUSB_CLASS_VENDOR_SPEC {
                continue;
            }

            devices.push(AvailableDevice {
                model,
                debug,
                transport: AvailableDeviceTransport::WebUsb(AvailableWebUsbTransport {
                    bus: dev.bus_number(),
                    address: dev.address(),
                }),
            });
        }
        Ok(devices)
    }

    /// Connect to a device over the WebUSB transport.
    pub fn connect(device: &AvailableDevice) -> Result<Box<dyn Transport>, Error> {
        let transport = match &device.transport {
            AvailableDeviceTransport::WebUsb(t) => t,
            _ => panic!("passed wrong AvailableDevice in WebUsbTransport::connect"),
        };

        let interface = match device.debug {
            false => constants::INTERFACE,
            true => constants::INTERFACE_DEBUG,
        };

        // Go over the devices again to match the desired device.
        let dev = rusb::devices()?
            .iter()
            .find(|dev| dev.bus_number() == transport.bus && dev.address() == transport.address)
            .ok_or(Error::DeviceDisconnected)?;
        // Check if there is not another device connected on this bus.
        let dev_desc = dev.device_descriptor()?;
        let dev_id = (dev_desc.vendor_id(), dev_desc.product_id());
        if derive_model(dev_id).as_ref() != Some(&device.model) {
            return Err(Error::DeviceDisconnected);
        }
        let handle = dev.open()?;
        handle.claim_interface(interface)?;

        let mut link = WebUsbLink {
            handle,
            endpoint: match device.debug {
                false => constants::ENDPOINT,
                true => constants::ENDPOINT_DEBUG,
            },
        };
        // Drain any chunks already queued on the IN endpoint after claiming
        // the interface, so the first exchange starts from a clean state.
        link.drain();

        Ok(Box::new(WebUsbTransport { protocol: ProtocolV1 { link } }))
    }
}

impl super::Transport for WebUsbTransport {
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
