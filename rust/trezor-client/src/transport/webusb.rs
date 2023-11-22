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
use std::{fmt, result::Result, time::Duration};

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

const READ_TIMEOUT_MS: u64 = 100000;
const WRITE_TIMEOUT_MS: u64 = 100000;

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
        let timeout = Duration::from_millis(WRITE_TIMEOUT_MS);
        if let Err(e) = self.handle.write_interrupt(self.endpoint, &chunk, timeout) {
            return Err(e.into())
        }
        Ok(())
    }

    fn read_chunk(&mut self) -> Result<Vec<u8>, Error> {
        let mut chunk = vec![0; CHUNK_SIZE];
        let endpoint = constants::READ_ENDPOINT_MASK | self.endpoint;
        let timeout = Duration::from_millis(READ_TIMEOUT_MS);

        let n = self.handle.read_interrupt(endpoint, &mut chunk, timeout)?;
        if n == CHUNK_SIZE {
            Ok(chunk)
        } else {
            Err(Error::DeviceReadTimeout)
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
                continue
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
            return Err(Error::DeviceDisconnected)
        }
        let mut handle = dev.open()?;
        handle.claim_interface(interface)?;

        Ok(Box::new(WebUsbTransport {
            protocol: ProtocolV1 {
                link: WebUsbLink {
                    handle,
                    endpoint: match device.debug {
                        false => constants::ENDPOINT,
                        true => constants::ENDPOINT_DEBUG,
                    },
                },
            },
        }))
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
