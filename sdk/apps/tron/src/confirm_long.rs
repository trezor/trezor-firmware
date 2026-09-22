// TMP: demo handler for trezor_app_sdk::ui::confirm_long, exercised by
// sdk/apps/tron/tests/test_confirm_long.py. Not a real Tron feature.

use crate::proto::{
    common::button_request::ButtonRequestType,
    tron::{ConfirmLong, ConfirmLongAck},
};
use trezor_app_sdk::{Result, ResultExt, ui};

pub(crate) fn confirm_long(msg: ConfirmLong) -> Result<ConfirmLongAck> {
    ui::error_if_not_confirmed(
        ui::confirm_long(
            &msg.title,
            &msg.content,
            Some("confirm_long"),
            ButtonRequestType::Other.into(),
        )
        .c()?,
    )
    .c()?;

    Ok(ConfirmLongAck {})
}
