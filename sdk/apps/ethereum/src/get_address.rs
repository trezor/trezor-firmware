use crate::{
    common::{COIN, get_eth_pubkey_hash},
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
    let definitions = Definitions::from_encoded(encoded_network, None, None, slip44)
        .context("Failed to decode definitions")?;

    crypto::verify_derivation_path(dp.as_slice(), encoded_network, None, None)
        .context("Failed to verify derivation path")?;

    let pubkey_hash = get_eth_pubkey_hash(&dp).context("Failed to get eth pubkey hash")?;
    let address = address_from_bytes(&pubkey_hash, Some(definitions.network()))
        .context("Failed to convert bytes to address")?;
    let slip44_id = &msg.address_n[1]; // it depends on the network (ETH vs ETC...)
    let mac = crypto::get_address_mac(dp.as_ref(), &address, encoded_network)
        .context("Failed to get address MAC")?;

    if let Some(true) = msg.show_display {
        // TODO: template translation
        let subtitle = uformat!("{} address", COIN);
        let account_name = dp
            .get_account_name(COIN, &PATTERNS_ADDRESS, *slip44_id)
            .ok_or(crate::Error::DataError("Failed to get account name"))?;
        let chunkify = msg.chunkify.unwrap_or_default();
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
        .context("Address was not confirmed")?;

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
