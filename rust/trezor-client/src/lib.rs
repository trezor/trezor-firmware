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

    use base64::prelude::*;
    use bitcoin::{
        bip32::DerivationPath,
        hex::{DisplayHex as _, FromHex},
        network, Psbt,
    };
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
    fn test_miniscript_register_policy() {
        let mut emulator = init_emulator();
        let network = network::Network::Signet;
        assert_eq!(emulator.features().expect("Failed to get features").label(), "SLIP-0014");
        let registered = with_auto_approve(|| {
            emulator.register_policy("Policy name".to_owned(),
            "wsh(or_d(pk(@0/**),and_v(v:pkh(@1/**),older(1))))".to_owned(),
            vec![
                "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg".to_owned(),
                "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb".to_owned(),
            ],
            network
        )}).unwrap();

        let path = DerivationPath::from_str("m/84'/1'/0'/0/1").expect("Failed to parse path");
        let addr = emulator
            .get_address(&path, InputScriptType::SPENDMINISCRIPT, network, false, Some(registered))
            .unwrap();

        assert_eq!(
            addr.to_string(),
            "tb1qzvr7ptes6kq2ee0745a7h2n639etfz43nsz9d2jn8u6wz8egx0hqnr5pza"
        );
    }

    #[test]
    #[serial]
    fn test_miniscript_sign_psbt_simple() {
        let mut emulator = init_emulator();
        let network = network::Network::Signet;
        assert_eq!(emulator.features().expect("Failed to get features").label(), "SLIP-0014");
        let registered = with_auto_approve(|| {
            emulator.register_policy("Policy name".to_owned(),
            "wsh(or_d(pk(@0/**),and_v(v:pkh(@1/**),older(52596))))".to_owned(),
            vec![
                "tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76".to_owned(),
                "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb".to_owned(),
            ],
            network
        )}).unwrap();

        let psbt_b64 = "cHNidP8BAFICAAAAAeLueDmXeu2TBFNQoar0iky5T9JE59JPX0yr/gzIIr7UAAAAAAD9////AUYhAAAAAAAAFgAUhH7Jd+SNi4/DMKLI3HIJdwhi1+6kowQAAAEAywIAAAAAAQHYqmd/WZL+qJOT+5f2XEPzUALTONhlyumq5tyciNVZ8wAAAAAA/f///wE0IgAAAAAAACIAIDUq27pDBHpIicznRJ7W0Vfte6npLsF1yY7B5qOLXbjQAkcwRAIgEAu12ThbMeLnoUW4gXGoyRNtgLoJiMVTGBmN/EF1Ud8CIFacrJc9i3SqN3KU6pUlTnNm6GK1N4Vxa5D2tgz2MYc/ASEDwaxgrIFP7ymqIm9BGZ+2SbpwuLq5OiGykBIZVIRQOEqjowQAAQErNCIAAAAAAAAiACA1Ktu6QwR6SInM50Se1tFX7Xup6S7BdcmOweaji1240AEFRCEDC75bhURKbsY1a1FJFsQxD6kiEzUz4inlmKfSqZlD5JWsc2R2qRStjQxCX2+O2vUnBSggjUbj8GSQbIitA3TNALJoIgYCI1EpH6IXHxLBFqXb1/FWdb0zvMoXyhBDC5/EcW5MSpUYcnWLw1QAAIABAACAAAAAgAAAAAABAAAAIgYDC75bhURKbsY1a1FJFsQxD6kiEzUz4inlmKfSqZlD5JUcXJ4ijTAAAIABAACAAAAAgAIAAIAAAAAAAQAAAAAA";
        let psbt = Psbt::deserialize(&BASE64_STANDARD.decode(psbt_b64).unwrap()).unwrap();

        let signed =
            with_auto_approve(|| emulator.sign_tx(&psbt, network, Some(registered)).unwrap());
        assert_eq!(signed.serialized, vec![]);
        assert_eq!(signed.signatures.len(), 1);
        let (i, sig) = signed.signatures.get(0).unwrap();
        assert_eq!(*i, 0);
        assert_eq!(sig.to_lower_hex_string(), "30440220106ef246defefb79999e95d92a1fd63684ea17d5944133762ad589d10b6e2faa02200a73ee663bb732cf78f9f3a61dbc1cc5ca254a9b22b9737ac24149d144c2be18");
    }

    #[test]
    #[serial]
    fn test_miniscript_sign_psbt_expand_primary() {
        let mut emulator = init_emulator();
        let network = network::Network::Signet;
        assert_eq!(emulator.features().expect("Failed to get features").label(), "SLIP-0014");
        let registered = with_auto_approve(|| {
            emulator.register_policy("Policy name".to_owned(),
            "wsh(or_i(and_v(v:thresh(2,pkh([72758bc3/48'/1'/0'/2']tpubDFEgneqafaLtGYbwidefdMyBZ3mxyoqyQZPPqjZ7AVKjwxSzDgRhgobENPu8Fn8gkJJtgKaFa6fbS9AuccZSeJqqXGy2x9BCgiJ6By3qRAJ/<2;3>/*),a:pkh([5c9e228d/48'/1'/0'/2']tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76/<2;3>/*),a:pkh([beda3749/48'/1'/0'/2']tpubDF9MY7ez2hYzCEi8T3msePgjy1eeZA1tVqeeN3mTPHcUagWbGTcBfj3qNyBCA3DgmrzTFyApcK5pBBrcmh2VYv1UaVdnwozX7WsJYi3M5z8/<0;1>/*)),older(1)),and_v(v:pk([72758bc3/48'/1'/0'/2']tpubDFEgneqafaLtGYbwidefdMyBZ3mxyoqyQZPPqjZ7AVKjwxSzDgRhgobENPu8Fn8gkJJtgKaFa6fbS9AuccZSeJqqXGy2x9BCgiJ6By3qRAJ/<0;1>/*),pk([5c9e228d/48'/1'/0'/2']tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76/<0;1>/*))))#asx72vh2".to_owned(),
            vec![],
            network
        )}).unwrap();

        let psbt_b64 = "cHNidP8BAFICAAAAAfm+jqsTisvBnVsSENyEkRaeQNT/8VskfQuzelm/j+PlAAAAAAD9////AewZAAAAAAAAFgAUs6SfN38brSLL89ITPjwxFLBBSiBFpQQAAAEAywIAAAAAAQG2c6O6CuxG68HXKs3L9pXMzN9hfmow1iBYD93rGJj88gEAAAAA/f///wEsGwAAAAAAACIAIAYsq+xuzMqY3lobEteJJUprcq591G9YUGNz3XMPuul0AkcwRAIga1w0FACUcHgQgbf0CujgaR83RLSzc7W7sMZCVe/XuaQCIDdBzuzdysEwHtldYmqyjQssIkGhofnRyPf6XJZDViTgASED2aCjBPZ67F8FxaMiruP4IBBcrmTg5CfpAZtos3B1405FpQQAAQErLBsAAAAAAAAiACAGLKvsbszKmN5aGxLXiSVKa3KufdRvWFBjc91zD7rpdAEFnmN2qRTIaXyqb7uGd+RX6efeHC9NFKXtJYisa3apFMFabION3Ib2QdZ2vXTdZ2dxFa2aiKxsk2t2qRQgG20S9KhQtZyE94VxUlExqy3iYYisbJNSiFGyZyECtrFWTYo0lBv+zYDmyuyqjdpJMgng4jLJC2FFGZRBx2GtIQMLvluFREpuxjVrUUkWxDEPqSITNTPiKeWYp9KpmUPklaxoIgYCtrFWTYo0lBv+zYDmyuyqjdpJMgng4jLJC2FFGZRBx2EccnWLwzAAAIABAACAAAAAgAIAAIAAAAAAAQAAACIGAwu+W4VESm7GNWtRSRbEMQ+pIhM1M+Ip5Zin0qmZQ+SVHFyeIo0wAACAAQAAgAAAAIACAACAAAAAAAEAAAAiBgOuepQ7PTbTbj3i/1ndXjKZqklfp9IJ8x5MKqO3J6XAdBy+2jdJMAAAgAEAAIAAAACAAgAAgAAAAAABAAAAAAA=";
        let psbt = Psbt::deserialize(&BASE64_STANDARD.decode(psbt_b64).unwrap()).unwrap();

        let signed =
            with_auto_approve(|| emulator.sign_tx(&psbt, network, Some(registered)).unwrap());
        assert_eq!(signed.serialized, vec![]);
        assert_eq!(signed.signatures.len(), 1);
        let (i, sig) = signed.signatures.get(0).unwrap();
        assert_eq!(*i, 0);
        assert_eq!(sig.to_lower_hex_string(), "304402207558489ad4d96fe5c6569a1c8597fbe0a11822c10a2bdca3f03725043f37f6b4022002b955679963a3bc8fded5427b5721399bd980f9987ac7d1fe944a2d0d93be4b");
    }

    #[test]
    #[serial]
    fn test_miniscript_sign_psbt_expand_recovery() {
        let mut emulator = init_emulator();
        let network = network::Network::Signet;
        assert_eq!(emulator.features().expect("Failed to get features").label(), "SLIP-0014");
        let registered = with_auto_approve(|| {
            let mut apply = protos::ApplySettings::new();
            apply.safety_checks = Some(protos::SafetyCheckLevel::PromptTemporarily.into());
            emulator.call(apply, Box::new(|_, m: protos::Success| Ok(m))).unwrap().interact().unwrap();
            emulator.register_policy("Policy name".to_owned(),
            "wsh(or_i(and_v(v:thresh(2,pkh([72758bc3/48'/1'/0'/2']tpubDFEgneqafaLtGYbwidefdMyBZ3mxyoqyQZPPqjZ7AVKjwxSzDgRhgobENPu8Fn8gkJJtgKaFa6fbS9AuccZSeJqqXGy2x9BCgiJ6By3qRAJ/<2;3>/*),a:pkh([5c9e228d/48'/1'/0'/2']tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76/<2;3>/*),a:pkh([beda3749/48'/1'/0'/2']tpubDF9MY7ez2hYzCEi8T3msePgjy1eeZA1tVqeeN3mTPHcUagWbGTcBfj3qNyBCA3DgmrzTFyApcK5pBBrcmh2VYv1UaVdnwozX7WsJYi3M5z8/<0;1>/*)),older(1)),and_v(v:pk([72758bc3/48'/1'/0'/2']tpubDFEgneqafaLtGYbwidefdMyBZ3mxyoqyQZPPqjZ7AVKjwxSzDgRhgobENPu8Fn8gkJJtgKaFa6fbS9AuccZSeJqqXGy2x9BCgiJ6By3qRAJ/<0;1>/*),pk([5c9e228d/48'/1'/0'/2']tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76/<0;1>/*))))#asx72vh2".to_owned(),
            vec![],
            network
        )}).unwrap();

        let psbt_b64 = "cHNidP8BAFICAAAAAfm+jqsTisvBnVsSENyEkRaeQNT/8VskfQuzelm/j+PlAAAAAAABAAAAAZQZAAAAAAAAFgAUs6SfN38brSLL89ITPjwxFLBBSiBJpQQAAAEAywIAAAAAAQG2c6O6CuxG68HXKs3L9pXMzN9hfmow1iBYD93rGJj88gEAAAAA/f///wEsGwAAAAAAACIAIAYsq+xuzMqY3lobEteJJUprcq591G9YUGNz3XMPuul0AkcwRAIga1w0FACUcHgQgbf0CujgaR83RLSzc7W7sMZCVe/XuaQCIDdBzuzdysEwHtldYmqyjQssIkGhofnRyPf6XJZDViTgASED2aCjBPZ67F8FxaMiruP4IBBcrmTg5CfpAZtos3B1405FpQQAAQErLBsAAAAAAAAiACAGLKvsbszKmN5aGxLXiSVKa3KufdRvWFBjc91zD7rpdAEFnmN2qRTIaXyqb7uGd+RX6efeHC9NFKXtJYisa3apFMFabION3Ib2QdZ2vXTdZ2dxFa2aiKxsk2t2qRQgG20S9KhQtZyE94VxUlExqy3iYYisbJNSiFGyZyECtrFWTYo0lBv+zYDmyuyqjdpJMgng4jLJC2FFGZRBx2GtIQMLvluFREpuxjVrUUkWxDEPqSITNTPiKeWYp9KpmUPklaxoIgYCnDCZW33P5Papm4o1bK40seR7vdluRj49ZD8INT+IHWEcXJ4ijTAAAIABAACAAAAAgAIAAIACAAAAAQAAACIGA656lDs9NtNuPeL/Wd1eMpmqSV+n0gnzHkwqo7cnpcB0HL7aN0kwAACAAQAAgAAAAIACAACAAAAAAAEAAAAiBgO7/OWz4L1d1fgiz39lWkafPHCYGVpIqQMDk5FyBCCEExxydYvDMAAAgAEAAIAAAACAAgAAgAIAAAABAAAAAAA=";
        let psbt = Psbt::deserialize(&BASE64_STANDARD.decode(psbt_b64).unwrap()).unwrap();

        let signed =
            with_auto_approve(|| emulator.sign_tx(&psbt, network, Some(registered)).unwrap());
        assert_eq!(signed.serialized, vec![]);
        assert_eq!(signed.signatures.len(), 1);
        let (i, sig) = signed.signatures.get(0).unwrap();
        assert_eq!(*i, 0);
        assert_eq!(sig.to_lower_hex_string(), "304402201e8cb4605837b9d4c2227d9d0c431d61558afc609ff0763ef5ed45d5ba41c86802205bf04c4159863c9bcf51a4f40a1583a1b26d964f5a8e408d34f62e787aec2f02");
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
