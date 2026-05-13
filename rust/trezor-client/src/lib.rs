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
    use std::{
        str::FromStr,
        sync::{
            atomic::{AtomicBool, Ordering},
            Arc,
        },
        thread,
    };

    use bitcoin::{bip32::DerivationPath, hex::FromHex, network};
    use serial_test::serial;

    use crate::{
        client::handle_interaction,
        protos::{
            debug_link_decision::DebugButton, DebugLinkDecision, DebugLinkGetState, DebugLinkState,
            IdentityType,
        },
    };

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

    /// Spawn a background thread that continuously sends a "YES" decision to the debug link.
    fn with_auto_approve<F, T>(f: F) -> T
    where
        F: FnOnce() -> T,
    {
        let mut debuglink = find_devices(true)
            .into_iter()
            .find(|t| t.model == Model::TrezorEmulator)
            .expect("No debug emulator found")
            .connect()
            .expect("Failed to connect to debug emulator");

        let stop = Arc::new(AtomicBool::new(false));
        let stop_clone = stop.clone();

        let mut req = DebugLinkDecision::new();
        req.set_button(DebugButton::YES);

        thread::scope(|scope| {
            scope.spawn(move || {
                while !stop_clone.load(Ordering::Relaxed) {
                    // DebugLinkDecision has no response; send fire-and-forget then poll
                    // state (which returns when the firmware has processed the decision).
                    let _ = debuglink.send_message(req.clone());
                    let _ = debuglink
                        .call(DebugLinkGetState::new(), Box::new(|_, m: DebugLinkState| Ok(m)));
                }
            });
            let res = f();
            stop.store(true, Ordering::Relaxed);
            res
        })
    }

    #[test]
    #[serial]
    fn test_emulator_find() {
        let trezors = find_devices(false);
        assert!(!trezors.is_empty());
        assert!(trezors.iter().any(|t| t.model == Model::TrezorEmulator));
    }

    #[test]
    #[serial]
    fn test_emulator_features() {
        let emulator = init_emulator();
        let features = emulator.features().expect("Failed to get features");
        assert_eq!(features.vendor(), "trezor.io");
        assert!(features.initialized());
        assert!(!features.firmware_present());
        assert!(features.initialized());
        assert!(!features.pin_protection());
        assert!(!features.passphrase_protection());
        assert!(["T", "Safe 3", "Safe 5"].contains(&features.model()));
    }

    #[test]
    #[serial]
    fn test_bitcoin_address() {
        let mut emulator = init_emulator();
        assert_eq!(emulator.features().expect("Failed to get features").label(), "SLIP-0014");
        let path = DerivationPath::from_str("m/44'/1'/0'/0/0").expect("Failed to parse path");
        let address = emulator
            .get_address(
                &path,
                InputScriptType::SPENDADDRESS,
                bitcoin::Network::Testnet,
                false,
                None,
            )
            .expect("Failed to get address");
        assert_eq!(address.to_string(), "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q");
    }

    #[test]
    #[serial]
    fn test_register_policy() {
        let mut emulator = init_emulator();
        assert_eq!(emulator.features().expect("Failed to get features").label(), "SLIP-0014");
        let registered = with_auto_approve(|| {
            emulator.register_policy("Policy name".to_owned(),
            "wsh(or_d(pk(@0/**),and_v(v:pkh(@1/**),older(1))))".into(), vec![
            "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg".to_owned(),
            "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb".to_owned(),
        ], network::Network::Signet).unwrap()
        });

        let path = DerivationPath::from_str("m/84'/1'/0'/0/1").expect("Failed to parse path");
        let addr = emulator
            .get_address(
                &path,
                InputScriptType::SPENDMINISCRIPT,
                network::Network::Signet,
                false,
                Some(registered),
            )
            .unwrap();

        assert_eq!(
            addr.to_string(),
            "tb1qzvr7ptes6kq2ee0745a7h2n639etfz43nsz9d2jn8u6wz8egx0hqnr5pza"
        );
    }

    #[test]
    #[serial]
    fn test_ecdh_shared_secret() {
        let mut emulator = init_emulator();
        assert_eq!(emulator.features().expect("Failed to get features").label(), "SLIP-0014");

        let mut ident = IdentityType::new();
        ident.set_proto("gpg".to_owned());
        ident.set_user("".to_owned());
        ident.set_host("Satoshi Nakamoto <satoshi@bitcoin.org>".to_owned());
        ident.set_port("".to_owned());
        ident.set_path("".to_owned());
        ident.set_index(0);

        let peer_public_key = Vec::from_hex("0407f2c6e5becf3213c1d07df0cfbe8e39f70a8c643df7575e5c56859ec52c45ca950499c019719dae0fda04248d851e52cf9d66eeb211d89a77be40de22b6c89d").unwrap();
        let curve_name = "secp256k1".to_owned();

        let response = with_auto_approve(|| {
            handle_interaction(
                emulator
                    .get_ecdh_session_key(ident, peer_public_key, curve_name)
                    .expect("Failed to get ECDH shared secret"),
            )
        })
        .unwrap();

        let expected_session_key = Vec::from_hex("048125883b086746244b0d2c548860ecc723346e14c87e51dc7ba32791bc780d132dbd814fbee77134f318afac6ad6db3c5334efe6a8798628a1038195b96e82e2").unwrap();
        assert_eq!(response.session_key(), &expected_session_key);

        let expected_public_key =
            Vec::from_hex("032726ba71aa066b47fc0f90b389f8c3e02fe20b94c858395d71f260e9944e3c65")
                .unwrap();
        assert_eq!(response.public_key(), &expected_public_key);
    }

    #[test]
    #[serial]
    fn test_ethereum_sign_tx_large() {
        let mut emulator = init_emulator();
        assert_eq!(emulator.features().expect("Failed to get features").label(), "SLIP-0014");

        let signature = with_auto_approve(|| {
            emulator.ethereum_sign_tx(
                // default ETH path
                vec![44 + (1 << 31), 60 + (1 << 31), 0 + (1 << 31), 0, 0],
                vec![],
                vec![],
                vec![],
                "".to_string(),
                vec![],
                // 10kB of empty data
                vec![0; 10 * 1024],
                Some(1u64),
            )
        })
        .unwrap();

        assert_eq!(signature.r.len(), 32);
        assert_eq!(signature.s.len(), 32);
        assert_eq!(signature.v, 38);
    }
}
