use super::{AvailableDevice, Model};
use crate::protos::MessageType;
use std::fmt;

pub mod error;
pub mod protocol;
pub mod udp;
pub mod webusb;

/// An available transport for a Trezor device, containing any of the different supported
/// transports.
#[derive(Debug)]
pub enum AvailableDeviceTransport {
    WebUsb(webusb::AvailableWebUsbTransport),
    Udp(udp::AvailableUdpTransport),
}

impl fmt::Display for AvailableDeviceTransport {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AvailableDeviceTransport::WebUsb(ref t) => write!(f, "{}", t),
            AvailableDeviceTransport::Udp(ref t) => write!(f, "{}", t),
        }
    }
}

/// A protobuf message accompanied by the message type.  This type is used to pass messages over the
/// transport and used to contain messages received from the transport.
pub struct ProtoMessage(pub MessageType, pub Vec<u8>);

impl ProtoMessage {
    pub fn new(mt: MessageType, payload: Vec<u8>) -> ProtoMessage {
        ProtoMessage(mt, payload)
    }
    pub fn message_type(&self) -> MessageType {
        self.0
    }
    pub fn payload(&self) -> &[u8] {
        &self.1
    }
    pub fn into_payload(self) -> Vec<u8> {
        self.1
    }

    /// Take the payload from the ProtoMessage and parse it to a protobuf message.
    pub fn into_message<M: protobuf::Message>(self) -> Result<M, protobuf::Error> {
        protobuf::Message::parse_from_bytes(&self.into_payload())
    }
}

/// The transport interface that is implemented by the different ways to communicate with a Trezor
/// device.
pub trait Transport: Sync + Send {
    fn session_begin(&mut self) -> Result<(), error::Error>;
    fn session_end(&mut self) -> Result<(), error::Error>;

    fn write_message(&mut self, message: ProtoMessage) -> Result<(), error::Error>;
    fn read_message(&mut self) -> Result<ProtoMessage, error::Error>;
}

/// A delegation method to connect an available device transport.  It delegates to the different
/// transport types.
pub fn connect(available_device: &AvailableDevice) -> Result<Box<dyn Transport>, error::Error> {
    match available_device.transport {
        AvailableDeviceTransport::WebUsb(_) => webusb::WebUsbTransport::connect(available_device),
        AvailableDeviceTransport::Udp(_) => udp::UdpTransport::connect(available_device),
    }
}

// A collection of transport-global constants.
mod constants {
    pub const DEV_TREZOR_LEGACY: (u16, u16) = (0x534C, 0x0001);
    pub const DEV_TREZOR: (u16, u16) = (0x1209, 0x53C1);
    pub const DEV_TREZOR_BOOTLOADER: (u16, u16) = (0x1209, 0x53C0);
}

/// Derive the Trezor model from the USB device.
pub(crate) fn derive_model(dev_id: (u16, u16)) -> Option<Model> {
    match dev_id {
        constants::DEV_TREZOR_LEGACY => Some(Model::TrezorLegacy),
        constants::DEV_TREZOR => Some(Model::Trezor),
        constants::DEV_TREZOR_BOOTLOADER => Some(Model::TrezorBootloader),
        _ => None,
    }
}
