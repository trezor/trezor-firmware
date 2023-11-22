//! # Trezor API library
//!
//! ## Connecting
//!
//! Use the public top-level methods `find_devices()` and `unique()` to find devices.  When using
//! `find_devices()`, a list of different available devices is returned.  To connect to one or more
//! of them, use their `connect()` method.
//!
//! ## Logging
//!
//! We use the log package interface, so any logger that supports log can be attached.
//! Please be aware that `trace` logging can contain sensitive data.

#![warn(unreachable_pub, rustdoc::all)]
#![cfg_attr(not(test), warn(unused_crate_dependencies))]
#![deny(unused_must_use, rust_2018_idioms)]
#![cfg_attr(docsrs, feature(doc_cfg, doc_auto_cfg))]

mod messages;

pub mod client;
pub mod error;
pub mod protos;
pub mod transport;
#[cfg(feature = "bitcoin")]
pub mod utils;

mod flows {
    #[cfg(feature = "bitcoin")]
    pub(crate) mod sign_tx;
}

pub use client::{
    ButtonRequest, ButtonRequestType, EntropyRequest, Features, PassphraseRequest,
    PinMatrixRequest, PinMatrixRequestType, Trezor, TrezorResponse, WordCount,
};
pub use error::{Error, Result};
pub use messages::TrezorMessage;

#[cfg(feature = "bitcoin")]
pub use flows::sign_tx::SignTxProgress;
#[cfg(feature = "bitcoin")]
pub use protos::InputScriptType;

use std::fmt;
use tracing::{debug, warn};
use transport::{udp::UdpTransport, webusb::WebUsbTransport};

/// The different kind of Trezor device models.
#[derive(PartialEq, Eq, Clone, Debug, Copy)]
pub enum Model {
    TrezorLegacy,
    Trezor,
    TrezorBootloader,
    TrezorEmulator,
}

impl fmt::Display for Model {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

impl Model {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Model::TrezorLegacy => "Trezor (legacy)",
            Model::Trezor => "Trezor",
            Model::TrezorBootloader => "Trezor (bootloader)",
            Model::TrezorEmulator => "Trezor Emulator",
        }
    }
}

/// A device found by the `find_devices()` method.  It can be connected to using the `connect()`
/// method.
#[derive(Debug)]
pub struct AvailableDevice {
    pub model: Model,
    pub debug: bool,
    transport: transport::AvailableDeviceTransport,
}

impl fmt::Display for AvailableDevice {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} (transport: {}) (debug: {})", self.model, &self.transport, self.debug)
    }
}

impl AvailableDevice {
    /// Connect to the device.
    pub fn connect(self) -> Result<Trezor> {
        let transport = transport::connect(&self).map_err(Error::TransportConnect)?;
        Ok(client::trezor_with_transport(self.model, transport))
    }
}

/// Search for all available devices.
/// Most devices will show up twice both either debugging enables or disabled.
pub fn find_devices(debug: bool) -> Vec<AvailableDevice> {
    let mut devices = vec![];

    match WebUsbTransport::find_devices(debug) {
        Ok(usb) => devices.extend(usb),
        Err(err) => {
            warn!("{}", Error::TransportConnect(err))
        }
    };

    match UdpTransport::find_devices(debug, None) {
        Ok(udp) => devices.extend(udp),
        Err(err) => {
            warn!("{}", Error::TransportConnect(err))
        }
    };

    devices
}

/// Try to get a single device.  Optionally specify whether debug should be enabled or not.
/// Can error if there are multiple or no devices available.
/// For more fine-grained device selection, use `find_devices()`.
/// When using USB mode, the device will show up both with debug and without debug, so it's
/// necessary to specify the debug option in order to find a unique one.
pub fn unique(debug: bool) -> Result<Trezor> {
    let mut devices = find_devices(debug);
    match devices.len() {
        0 => Err(Error::NoDeviceFound),
        1 => Ok(devices.remove(0).connect()?),
        _ => {
            debug!("Trezor devices found: {:?}", devices);
            Err(Error::DeviceNotUnique)
        }
    }
}

#[cfg(test)]
mod tests {
    use serial_test::serial;
    use std::str::FromStr;

    use bitcoin::bip32::DerivationPath;

    use super::*;

    fn init_emulator() -> Trezor {
        let mut emulator = find_devices(false)
            .into_iter()
            .find(|t| t.model == Model::TrezorEmulator)
            .expect("No emulator found")
            .connect()
            .expect("Failed to connect to emulator");
        emulator.init_device(None).expect("Failed to intialize device");
        emulator
    }

    #[test]
    #[serial]
    fn test_emulator_find() {
        let trezors = find_devices(false);
        assert!(trezors.len() > 0);
        assert!(trezors.iter().any(|t| t.model == Model::TrezorEmulator));
    }

    #[test]
    #[serial]
    fn test_emulator_features() {
        let emulator = init_emulator();
        let features = emulator.features().expect("Failed to get features");
        assert_eq!(features.vendor(), "trezor.io");
        assert_eq!(features.initialized(), true);
        assert_eq!(features.firmware_present(), false);
        assert_eq!(features.model(), "T");
        assert_eq!(features.initialized(), true);
        assert_eq!(features.pin_protection(), false);
        assert_eq!(features.passphrase_protection(), false);
    }

    #[test]
    #[serial]
    fn test_bitcoin_address() {
        let mut emulator = init_emulator();
        assert_eq!(emulator.features().expect("Failed to get features").label(), "SLIP-0014");
        let path = DerivationPath::from_str("m/44'/1'/0'/0/0").expect("Failed to parse path");
        let address = emulator
            .get_address(&path, InputScriptType::SPENDADDRESS, bitcoin::Network::Testnet, false)
            .expect("Failed to get address");
        assert_eq!(address.ok().unwrap().to_string(), "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q");
    }
}
