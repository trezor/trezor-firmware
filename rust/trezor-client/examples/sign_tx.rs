use std::io::{self, Write};

use bitcoin::{
    bip32, blockdata::script::Builder, consensus::encode::Decodable, network::Network, psbt,
    transaction::Version, Address, Amount, Sequence, Transaction, TxIn, TxOut,
};

use trezor_client::{Error, SignTxProgress, TrezorMessage, TrezorResponse};

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

fn tx_progress(
    psbt: &mut psbt::Psbt,
    progress: SignTxProgress,
    raw_tx: &mut Vec<u8>,
) -> Result<(), Error> {
    if let Some(part) = progress.get_serialized_tx_part() {
        raw_tx.write_all(part).unwrap();
    }

    if !progress.finished() {
        let progress = handle_interaction(progress.ack_psbt(psbt, Network::Testnet).unwrap());
        tx_progress(psbt, progress, raw_tx)
    } else {
        Ok(())
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

    let mut psbt = psbt::Psbt {
        unsigned_tx: Transaction {
                version: Version::ONE,
                lock_time: bitcoin::absolute::LockTime::from_consensus(0),
                input: vec![TxIn {
                    previous_output: "c5bdb27907b78ce03f94e4bf2e94f7a39697b9074b79470019e3dbc76a10ecb6:0".parse().unwrap(),
                    sequence: Sequence(0xffffffff),
                    script_sig: Builder::new().into_script(),
                    witness: Default::default(),
                }],
                output: vec![TxOut {
                    value: Amount::from_sat(14245301),
                    script_pubkey: addr.script_pubkey(),
                }],
            },
        inputs: vec![psbt::Input {
            non_witness_utxo: Some(Transaction::consensus_decode(&mut &hex::decode("020000000001011eb5a3e65946f88b00d67b321e5fd980b32a2316fb1fc9b712baa6a1033a04e30100000017160014f0f81ee77d552b4c81497451d1abf5c22ce8e352feffffff02b55dd900000000001976a9142c3cf5686f47c1de9cc90b4255cc2a1ef8c01b3188acfb0391ae6800000017a914a3a79e37ad366d9bf9471b28a9a8f64b50de0c968702483045022100c0aa7b262967fc2803c8a9f38f26682edba7cafb7d4870ebdc116040ad5338b502205dfebd08e993af2e6aa3118a438ad70ed9f6e09bc6abfd21f8f2957af936bc070121031f4e69fcf110bb31f019321834c0948b5487f2782489f370f66dc20f7ac767ca8bf81500").unwrap()[..]).unwrap()),
            ..Default::default()
        }],
        outputs: vec![
            psbt::Output {
                ..Default::default()
            },
        ],
        proprietary: Default::default(),
        unknown: Default::default(),
        version: 0,
        xpub: Default::default(),
    };

    println!("psbt before: {:?}", psbt);
    println!("unsigned txid: {}", psbt.unsigned_tx.txid());
    println!(
        "unsigned tx: {}",
        hex::encode(bitcoin::consensus::encode::serialize(&psbt.unsigned_tx))
    );

    let mut raw_tx = Vec::new();
    let progress = handle_interaction(trezor.sign_tx(&psbt, Network::Testnet).unwrap());
    tx_progress(&mut psbt, progress, &mut raw_tx).unwrap();

    println!("signed tx: {}", hex::encode(raw_tx));
}
