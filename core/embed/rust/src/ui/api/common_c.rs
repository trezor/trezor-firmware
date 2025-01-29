//! Reexporting the `screens` module according to the
//! current feature (Trezor model)

use crate::ui::{CommonUI, ModelUI};

use crate::ui::shape;

use crate::ui::util::from_c_str;

#[no_mangle]
extern "C" fn display_rsod_rust(
    title: *const cty::c_char,
    msg: *const cty::c_char,
    footer: *const cty::c_char,
) {
    let title = unsafe { from_c_str(title) }.unwrap_or("");
    let msg = unsafe { from_c_str(msg) }.unwrap_or("");
    let footer = unsafe { from_c_str(footer) }.unwrap_or("");

    // SAFETY:
    // This is the only situation we are allowed use this function
    // to allow nested calls to `run_with_bumps`/`render_on_display`,
    // because after the error message is displayed, the application will
    // shut down.
    unsafe { shape::unlock_bumps_on_failure() };

    ModelUI::screen_fatal_error(title, msg, footer);
    ModelUI::backlight_on();
}

#[no_mangle]
extern "C" fn screen_boot_stage_2(fade_in: bool) {
    ModelUI::screen_boot_stage_2(fade_in);
}
