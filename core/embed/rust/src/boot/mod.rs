

use crate::ui::display::icon;
use crate::ui::model_tt::theme::{ICON_TREZOR_EMPTY, ICON_TREZOR_FULL, BLUE, BLACK, WHITE};
use crate::ui::constant;


#[no_mangle]
pub extern "C" fn boot_firmware(
    stage: cty::uint16_t
) {

    if stage == 0 {
        icon(constant::screen().center(), ICON_TREZOR_EMPTY, WHITE, BLACK);
    }else {
        icon(constant::screen().center(), ICON_TREZOR_FULL, WHITE, BLACK);
    }
}
