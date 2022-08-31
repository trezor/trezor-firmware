pub mod boot;

pub mod pin;

use crate::ui::workflow::boot::boot_workflow;

#[no_mangle]
pub extern "C" fn boot_firmware() {
    boot_workflow();
}
