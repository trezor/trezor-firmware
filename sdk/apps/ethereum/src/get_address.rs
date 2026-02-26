use crate::{
    definitions::Definitions,
    helpers::address_from_bytes,
    keychain::{Keychain, PATTERNS_ADDRESS, schemas_from_network},
    paths::Bip32Path,
    proto::ethereum::{EthereumAddress, EthereumGetAddress},
    uformat,
};
use trezor_app_sdk::{Result, crypto};

/// Ethereum uses Bitcoin xpub format
pub fn get_address(msg: EthereumGetAddress) -> Result<EthereumAddress> {
    let dp = Bip32Path::from_slice(&msg.address_n);

    let slip44 = dp.slip44();
    let definitions = Definitions::from_encoded(None, None, None, slip44).unwrap();

    let schemas = schemas_from_network(&PATTERNS_ADDRESS, definitions.slip44())?;
    let keychain = Keychain::new(schemas);

    dp.validate(&keychain)?;

    let encoded_network = msg.encoded_network.as_ref().map(|buf| buf.as_ref());
    let pubkey_hash = crypto::get_eth_pubkey_hash(dp.as_ref(), encoded_network, None)?;

    let address = address_from_bytes(&pubkey_hash, Some(definitions.network()));

    let slip44_id = &msg.address_n[1]; // it depends on the network (ETH vs ETC...)

    let mac = crypto::get_address_mac(dp.as_ref(), &address, encoded_network)?;

    if let Some(true) = msg.show_display {
        let coin = "ETH";
        let subtitle = uformat!("{} Address", coin);
        let account_name = dp
            .get_account_name(coin, &PATTERNS_ADDRESS, *slip44_id)
            .unwrap();
        trezor_app_sdk::ui::show_address(
            &address,
            None,
            Some(subtitle.as_str()),
            Some(account_name.as_str()),
            Some(&dp.to_string()),
            &[],
            msg.chunkify,
        )?;
    }

    let mut res = EthereumAddress::default();
    res.address = Some(address);
    res.mac = Some(mac.to_vec());

    Ok(res)
}
