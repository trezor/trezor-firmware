use crate::{
    common::{COIN, SLIP44_ID, get_eth_pubkey_hash},
    definitions::Definitions,
    helpers::address_from_bytes,
    layout::addr_pad,
    paths::{Bip32Path, PATTERNS_ADDRESS},
    proto::{
        common::button_request::ButtonRequestType,
        ethereum::{Address, GetAddress},
    },
    uformat,
};
use trezor_app_sdk::{Result, ResultExt, crypto, ui};

/// Ethereum uses Bitcoin xpub format
pub(crate) fn get_address(msg: GetAddress) -> Result<Address> {
    let dp: Bip32Path = Bip32Path::from_slice(&msg.address_n);

    let slip44 = dp.slip44();
    let encoded_network = msg.encoded_network.as_deref();
    let definitions = Definitions::from_encoded(encoded_network, None, None, slip44).c()?;

    let pubkey_hash = get_eth_pubkey_hash(&dp).c()?;
    let address = address_from_bytes(&pubkey_hash, Some(definitions.network())).c()?;
    let mac = crypto::get_address_mac(dp.as_ref(), &address).c()?;

    if let Some(true) = msg.show_display {
        // TODO: template translation
        let subtitle = uformat!("{} address", COIN);
        let account_name = dp
            .get_account_name(COIN, &PATTERNS_ADDRESS, SLIP44_ID)
            .ok_or(crate::Error::DataError("Failed to get account name"))?;
        let chunkify = msg.chunkify();
        ui::error_if_not_confirmed(ui::show_address(ui::ShowAddress::new(
            &addr_pad(&address, chunkify)?,
            &address,
            None,
            Some(subtitle.as_str()),
            Some(account_name.as_str()),
            Some(&dp.format_path()),
            &[],
            chunkify,
            ButtonRequestType::Other.into(),
        ))?)
        .c()?;

        ui::show_success(ui::ShowSuccess::new(
            tr!("words__title_done"),
            tr!("address__confirmed"),
            tr!("instructions__continue_in_app"),
            Some(3200),
            None,
            ButtonRequestType::Other.into(),
        ))?;
    }

    let res = Address {
        address: Some(address),
        mac: Some(mac.to_vec()),
        ..Default::default()
    };

    Ok(res)
}
