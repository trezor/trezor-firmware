

use crate::ui::display::icon;
use crate::ui::model_tt::theme::{ICON_TREZOR_EMPTY, BLUE, BLACK, WHITE};
use crate::ui::constant;


#[no_mangle]
pub extern "C" fn boot_firmware(
    stage: cty::uint16_t
) {

    icon(constant::screen().center(), ICON_TREZOR_EMPTY, WHITE, BLACK);
}
