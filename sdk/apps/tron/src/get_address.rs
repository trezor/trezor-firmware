use crate::{
    common::{COIN, SLIP44_ID, get_encoded_address, get_pubkey_hash},
    paths::{Bip32Path, PATTERNS_ADDRESS},
    proto::tron::{Address, GetAddress},
};
use trezor_app_sdk::{Result, ResultExt, crypto, modui};

pub(crate) fn get_address(msg: GetAddress) -> Result<Address> {
    let dp: Bip32Path = Bip32Path::from_slice(&msg.address_n);

    let mut address_bytes = [0u8; 21];
    address_bytes[0] = 0x41;
    address_bytes[1..].copy_from_slice(&get_pubkey_hash(&dp).c()?);

    let address = get_encoded_address(&address_bytes).c()?;
    let mac = crypto::get_address_mac(dp.as_ref(), &address, SLIP44_ID).c()?;

    if let Some(true) = msg.show_display {
        let account_name = dp
            .get_account_name(COIN, &PATTERNS_ADDRESS, SLIP44_ID)
            .ok_or(crate::Error::DataError("Failed to get account name"))
            .c()?;
        let path = dp.format_path();
        modui::verify_address("address", &address, Some(&account_name), Some(&path)).c()?;
    }

    let res = Address {
        address,
        mac: Some(mac.to_vec()),
        ..Default::default()
    };

    Ok(res)
}
