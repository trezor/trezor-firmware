use std::str::FromStr;

use bitcoin::{bip32::DerivationPath, network::Network, Address};
use trezor_client::{client::common::handle_interaction, InputScriptType};

fn main() {
    tracing_subscriber::fmt().with_max_level(tracing::Level::TRACE).init();

    // init with debugging
    let mut trezor = trezor_client::unique(false).unwrap();
    trezor.init_device(None).unwrap();

    let pubkey = handle_interaction(
        trezor
            .get_public_key(
                &DerivationPath::from_str("m/44h/1h/0h/0/0").unwrap(),
                trezor_client::protos::InputScriptType::SPENDADDRESS,
                Network::Testnet,
                true,
            )
            .unwrap(),
    )
    .unwrap();
    let addr = Address::p2pkh(&pubkey.to_pub(), Network::Testnet);
    println!("address: {}", addr);

    let (addr, signature) = handle_interaction(
        trezor
            .sign_message(
                "regel het".to_owned(),
                &DerivationPath::from_str("m/44h/1h/0h/0/0").unwrap(),
                InputScriptType::SPENDADDRESS,
                Network::Testnet,
            )
            .unwrap(),
    )
    .unwrap();
    println!("Addr from device: {}", addr);
    println!("Signature: {:?}", signature);
}
