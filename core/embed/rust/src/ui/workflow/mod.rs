pub mod boot;

use crate::ui::display::icon;
use crate::ui::model_tt::theme::{ICON_TREZOR_EMPTY, ICON_TREZOR_FULL, BLACK, WHITE};

use crate::ui::constant;
use crate::ui::workflow::boot::boot_workflow;


#[no_mangle]
pub extern "C" fn boot_firmware() {


    icon(constant::screen().center(), ICON_TREZOR_FULL, WHITE, BLACK);

    boot_workflow();


}
