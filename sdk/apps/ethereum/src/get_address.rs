use crate::{
    common::COIN, definitions::Definitions, helpers::address_from_bytes, layout::addr_pad, paths::{Bip32Path, PATTERNS_ADDRESS}, proto::{
        common::button_request::ButtonRequestType,
        ethereum::{Address, GetAddress},
    }, uformat
};
use trezor_app_sdk::{Result, crypto, ui};

/// Ethereum uses Bitcoin xpub format
pub(crate) fn get_address(msg: GetAddress) -> Result<Address> {
    let dp: Bip32Path = Bip32Path::from_slice(&msg.address_n);

    let slip44 = dp.slip44();
    let encoded_network = msg.encoded_network.as_deref();
    let definitions = Definitions::from_encoded(encoded_network, None, None, slip44)?;

    crypto::verify_derivation_path(dp.as_slice(), encoded_network, None, None)?;

    let pubkey_hash = crypto::get_eth_pubkey_hash(dp.as_ref(), encoded_network, None)?;
    let address = address_from_bytes(&pubkey_hash, Some(definitions.network()));
    let slip44_id = &msg.address_n[1]; // it depends on the network (ETH vs ETC...)
    let mac = crypto::get_address_mac(dp.as_ref(), &address, encoded_network)?;

    if let Some(true) = msg.show_display {
        // TODO: template translation
        let subtitle = uformat!("{} address", COIN);
        let account_name = dp
            .get_account_name(COIN, &PATTERNS_ADDRESS, *slip44_id)
            .unwrap();
        let chunkify = msg.chunkify.unwrap_or_default();
        ui::show_address(
            &addr_pad(&address, chunkify),
            None,
            Some(subtitle.as_str()),
            Some(account_name.as_str()),
            Some(&dp.to_string()),
            &[],
            chunkify,
            ButtonRequestType::ButtonRequestOther.into(),
        )?;

        ui::show_success(
            tr!("words__title_done"),
            tr!("address__confirmed"),
            tr!("instructions__continue_in_app"),
            Some(3200),
            None,
            ButtonRequestType::ButtonRequestOther.into(),
        )?;
    }

    let mut res = Address::default();
    res.address = Some(address);
    res.mac = Some(mac.to_vec());

    Ok(res)
}
