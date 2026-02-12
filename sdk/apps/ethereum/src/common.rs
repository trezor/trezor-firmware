use trezor_app_sdk::ui;
use trezor_app_sdk::util;
use trezor_app_sdk::{Error, Result};

pub(crate) fn require_confirm_address(
    address_bytes: &[u8],
    title: Option<&'static str>,
    subtitle: Option<&'static str>,
    verb: Option<&'static str>,
    br_name: Option<&'static str>,
    warning_footer: Option<&'static str>,
) -> Result<()> {
    let address = util::hex_encode(address_bytes);

    let res = ui::confirm_value(
        title.unwrap_or("Signing address"),
        // subtitle.unwrap_or(""),
        // verb.unwrap_or("Confirm"),
        // br_name.unwrap_or(""),
        // warning_footer.unwrap_or(""),
        address.as_str(),
    );
    if matches!(res, Ok(ui::TrezorUiResult::Confirmed)) {
        Ok(())
    } else {
        Err(Error::Cancelled)
    }
}
