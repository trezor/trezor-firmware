use crate::{
    consts::{COIN, SLIP44_ID},
    helpers::address_from_public_key,
    layout::fill,
    paths::{Bip32Path, PATTERNS_ADDRESS},
    proto::{
        common::button_request::ButtonRequestType,
        stellar::{Address, GetAddress},
    },
};
use trezor_app_sdk::{Result, ResultExt, crypto, ui};

pub(crate) fn get_address(msg: GetAddress) -> Result<Address> {
    let dp = Bip32Path::from_slice(&msg.address_n);

    let pubkey = crypto::get_public_key(dp.as_slice(), false).c()?;
    let address = address_from_public_key(&pubkey);
    let mac = crypto::get_address_mac(dp.as_ref(), &address).c()?;

    if msg.show_display.unwrap_or(false) {
        let subtitle = fill(tr!("address__coin_address_template"), COIN);
        let account_name = dp.get_account_name(COIN, &PATTERNS_ADDRESS, SLIP44_ID);
        ui::error_if_not_confirmed(
            ui::show_address(ui::ShowAddress::new(
                &address,
                &address,
                None,
                Some(subtitle.as_str()),
                account_name.as_deref(),
                Some(&dp.format_path()),
                &[],
                msg.chunkify.unwrap_or(false),
                ButtonRequestType::Address as i32,
                false,
            ))
            .c()?,
        )
        .c()?;
    }

    Ok(Address {
        address,
        mac: Some(mac.to_vec()),
    })
}
