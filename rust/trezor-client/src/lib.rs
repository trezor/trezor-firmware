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

pub use client::Trezor;
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

    use bitcoin::{
        bip32::{DerivationPath, Fingerprint},
        hex::FromHex,
        psbt,
    };
    use hex_lit::hex;
    use serial_test::serial;

    use crate::protos::{
        debug_link_decision::DebugButton, DebugLinkDecision, DebugLinkGetState, DebugLinkState,
        IdentityType,
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
                    let _ = debuglink.call::<_, DebugLinkState>(DebugLinkGetState::new());
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
            .get_address(&path, InputScriptType::SPENDADDRESS, bitcoin::Network::Testnet, false)
            .expect("Failed to get address");
        assert_eq!(address.to_string(), "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q");
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
            emulator
                .get_ecdh_session_key(ident, peer_public_key, curve_name)
                .expect("Failed to get ECDH shared secret")
        });

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

    fn unsigned_psbt(raw_tx: &[u8]) -> psbt::Psbt {
        use bitcoin::{consensus::deserialize, psbt, ScriptBuf, Transaction, Witness};

        let mut unsigned: Transaction = deserialize(&raw_tx).unwrap();
        for txi in &mut unsigned.input {
            txi.script_sig = ScriptBuf::new();
            txi.witness = Witness::new();
        }
        psbt::Psbt::from_unsigned_tx(unsigned).unwrap()
    }

    #[test]
    #[serial]
    fn test_bitcoin_signtx_one_one_fee() {
        use std::str::FromStr;

        use bitcoin::{consensus::deserialize, network::Network, Address};

        let mut emulator = init_emulator();

        let fpr = Fingerprint::from_hex("5c9e228d").unwrap();
        let deriv = DerivationPath::from_str("m/44h/0h/5h/0/9").unwrap();
        let pubkey = emulator.get_public_key(&deriv, Network::Bitcoin, false).unwrap().to_pub();

        let addr = Address::p2pkh(pubkey, Network::Bitcoin);
        assert_eq!(addr.to_string(), "1H2CRJBrDMhkvCGZMW7T4oQwYbL8eVuh7p");

        // Sign mainnet tx b893aeed4b12227b6f5348d7f6cb84ba2cda2ba70a41933a25f363b9d2fc2cf9

        let raw_tx = hex!("0100000001b5f59e2273c85b93aa9deff9bba5d7deace78610d3b0fb892a7ba6d86f36ac0d000000006b483045022100dd4dd136a70371bc9884c3c51fd52f4aed9ab8ee98f3ac7367bb19e6538096e702200c56be09c4359fc7eb494b4bdf8f2b72706b0575c4021373345b593e9661c7b6012103d7f3a07085bee09697cf03125d5c8760dfed65403dba787f1d1d8b1251af2cbeffffffff0148c40000000000001976a91419140511436e947448be994ab7fda9f98623e68e88ac00000000");
        let mut psbt = unsigned_psbt(&raw_tx);

        // Previous mainnet tx 0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5,

        let raw_orig_tx = hex!("0100000001dacfb5828cd2434f29d237968d4c785b8e12d6d45108df91a2fc09cc26f7f9eb000000006b4830450221009deff16fa96f178b429a8a816ca08762fd5fd2972e0090c878b36a56898ce553022055caab6afe0ed050e6dfbf91af9541166b17bda4ade447c08077902a9992f19b012102187fc04e6004c9bbe63178bc3fb3d3d6fd747f127ade47753c6f2dab37a3ac85ffffffff02f4f90000000000001976a914afbbf5e4c1315ec9f5e96428986660130dbee7b888ac05d70200000000001976a9143f1cccd6cc6174f2ac6454081d66444dc39a02bc88ac00000000");
        psbt.inputs[0].non_witness_utxo = Some(deserialize(&raw_orig_tx).unwrap());
        psbt.inputs[0].bip32_derivation.insert(pubkey.0, (fpr, deriv));

        let signed_tx = with_auto_approve(|| emulator.sign_tx(&psbt, Network::Bitcoin).unwrap());
        assert_eq!(signed_tx, raw_tx);
    }
}
