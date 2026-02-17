extern crate alloc;
use crate::strutil::hex_encode;
use crate::uformat;
use trezor_app_sdk::ui;
use trezor_app_sdk::{Error, Result};

pub(crate) fn require_confirm_address(
    address_bytes: &[u8],
    title: Option<&'static str>,
    subtitle: Option<&'static str>,
    verb: Option<&'static str>,
    br_name: Option<&'static str>,
    warning_footer: Option<&'static str>,
) -> Result<()> {
    let address_hex = uformat!("0x{}", hex_encode(address_bytes).as_str());
    let res = ui::confirm_value(title.unwrap_or("Signing address"), &address_hex);
    if matches!(res, Ok(ui::TrezorUiResult::Confirmed)) {
        Ok(())
    } else {
        Err(Error::Cancelled)
    }
}
