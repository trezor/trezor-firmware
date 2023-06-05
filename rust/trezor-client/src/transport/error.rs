//! # Error Handling

/// Trezor error.
#[derive(Debug, thiserror::Error)]
pub enum Error {
    /// [rusb] error.
    #[error(transparent)]
    Usb(#[from] rusb::Error),

    /// [std::io] error.
    #[error(transparent)]
    IO(#[from] std::io::Error),

    /// The device to connect to was not found.
    #[error("the device to connect to was not found")]
    DeviceNotFound,

    /// The device is no longer available.
    #[error("the device is no longer available")]
    DeviceDisconnected,

    /// The device produced a data chunk of unexpected size.
    #[error("the device produced a data chunk of unexpected size")]
    UnexpectedChunkSizeFromDevice(usize),

    /// Timeout expired while reading from device.
    #[error("timeout expired while reading from device")]
    DeviceReadTimeout,

    /// The device sent a chunk with a wrong magic value.
    #[error("the device sent a chunk with a wrong magic value")]
    DeviceBadMagic,

    /// The device sent a message with a wrong session id.
    #[error("the device sent a message with a wrong session id")]
    DeviceBadSessionId,

    /// The device sent an unexpected sequence number.
    #[error("the device sent an unexpected sequence number")]
    DeviceUnexpectedSequenceNumber,

    /// Received a non-existing message type from the device.
    #[error("received a non-existing message type from the device")]
    InvalidMessageType(u32),

    /// Unable to determine device serial number.
    #[error("unable to determine device serial number")]
    NoDeviceSerial,
}
