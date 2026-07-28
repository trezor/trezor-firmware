use crate::{
    common::{COIN, SLIP44_ID, get_encoded_address, get_pubkey_hash},
    paths::{Bip32Path, PATTERNS_ADDRESS},
    proto::{
        common::button_request::ButtonRequestType,
        tron::{Address, GetAddress},
    },
    uformat,
};
use trezor_app_sdk::{Result, ResultExt, crypto, ui};

pub(crate) fn get_address(msg: GetAddress) -> Result<Address> {
    let dp: Bip32Path = Bip32Path::from_slice(&msg.address_n);

    // crypto::verify_derivation_path(dp.as_slice(), None, None, None)
    //     .context("Failed to verify derivation path")?;

    let mut address_bytes = [0u8; 21];
    address_bytes[0] = 0x41;
    address_bytes[1..].copy_from_slice(&get_pubkey_hash(&dp).c()?);

    let address = get_encoded_address(&address_bytes).c()?;
    let mac = crypto::get_address_mac(dp.as_ref(), &address).c()?;

    if let Some(true) = msg.show_display {
        // TODO: template translation
        let subtitle = uformat!("{} address", COIN);
        let account_name = dp
            .get_account_name(COIN, &PATTERNS_ADDRESS, SLIP44_ID)
            .ok_or(crate::Error::DataError("Failed to get account name"))
            .c()?;
        ui::error_if_not_confirmed(ui::show_address(ui::ShowAddress::new(
            &address,
            &address,
            None,
            Some(subtitle.as_str()),
            Some(account_name.as_str()),
            Some(&dp.format_path()),
            &[],
            false,
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
        ))
        .c()?;
    }

    let res = Address {
        address,
        mac: Some(mac.to_vec()),
        ..Default::default()
    };

    Ok(res)
}
