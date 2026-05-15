use bitcoin::{bip32, network::Network, Address};

fn do_main() -> Result<(), trezor_client::Error> {
    // init with debugging
    let mut trezor = trezor_client::unique(true)?;
    trezor.init_device(None)?;

    let xpub = trezor.get_public_key(
        &vec![
            bip32::ChildNumber::from_hardened_idx(0).unwrap(),
            bip32::ChildNumber::from_hardened_idx(0).unwrap(),
            bip32::ChildNumber::from_hardened_idx(0).unwrap(),
        ]
        .into(),
        trezor_client::protos::InputScriptType::SPENDADDRESS,
        Network::Testnet,
        true,
    )?;
    println!("{}", xpub);
    println!("{:?}", xpub);
    println!("{}", Address::p2pkh(xpub.to_pub(), Network::Testnet));

    Ok(())
}

fn main() {
    do_main().unwrap()
}
