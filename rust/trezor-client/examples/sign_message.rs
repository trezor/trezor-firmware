use std::io;

use bitcoin::{bip32, network::constants::Network, Address};
use trezor_client::{InputScriptType, TrezorMessage, TrezorResponse};

fn handle_interaction<T, R: TrezorMessage>(resp: TrezorResponse<T, R>) -> T {
    match resp {
        TrezorResponse::Ok(res) => res,
        // assering ok() returns the failure error
        TrezorResponse::Failure(_) => resp.ok().unwrap(),
        TrezorResponse::ButtonRequest(req) => handle_interaction(req.ack().unwrap()),
        TrezorResponse::PinMatrixRequest(req) => {
            println!("Enter PIN");
            let mut pin = String::new();
            if io::stdin().read_line(&mut pin).unwrap() != 5 {
                println!("must enter pin, received: {}", pin);
            }
            // trim newline
            handle_interaction(req.ack_pin(pin[..4].to_owned()).unwrap())
        }
        TrezorResponse::PassphraseRequest(req) => {
            println!("Enter passphrase");
            let mut pass = String::new();
            io::stdin().read_line(&mut pass).unwrap();
            // trim newline
            handle_interaction(req.ack_passphrase(pass[..pass.len() - 1].to_owned()).unwrap())
        }
    }
}

fn main() {
    tracing_subscriber::fmt().with_max_level(tracing::Level::TRACE).init();

    // init with debugging
    let mut trezor = trezor_client::unique(false).unwrap();
    trezor.init_device(None).unwrap();

    let pubkey = handle_interaction(
        trezor
            .get_public_key(
                &vec![
                    bip32::ChildNumber::from_hardened_idx(0).unwrap(),
                    bip32::ChildNumber::from_hardened_idx(0).unwrap(),
                    bip32::ChildNumber::from_hardened_idx(1).unwrap(),
                ]
                .into(),
                trezor_client::protos::InputScriptType::SPENDADDRESS,
                Network::Testnet,
                true,
            )
            .unwrap(),
    );
    let addr = Address::p2pkh(&pubkey.to_pub(), Network::Testnet);
    println!("address: {}", addr);

    let (addr, signature) = handle_interaction(
        trezor
            .sign_message(
                "regel het".to_owned(),
                &vec![
                    bip32::ChildNumber::from_hardened_idx(0).unwrap(),
                    bip32::ChildNumber::from_hardened_idx(0).unwrap(),
                    bip32::ChildNumber::from_hardened_idx(1).unwrap(),
                ]
                .into(),
                InputScriptType::SPENDADDRESS,
                Network::Testnet,
            )
            .unwrap(),
    );
    println!("Addr from device: {}", addr);
    println!("Signature: {:?}", signature);
}
