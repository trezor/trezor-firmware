//! Reexporting the `screens` module according to the
//! current feature (Trezor model)

use rtl::util::CSlice;

#[cfg(feature = "ui_debug")]
use crate::ui::util::set_animation_disabled;
use crate::ui::{shape, CommonUI, ModelUI};

#[no_mangle]
extern "C" fn display_rsod_rust(
    title: *const cty::c_char,
    msg: *const cty::c_char,
    footer: *const cty::c_char,
) {
    let title = unsafe { CSlice::from_c_str(title) };
    let msg = unsafe { CSlice::from_c_str(msg) };
    let footer = unsafe { CSlice::from_c_str(footer) };

    // SAFETY:
    // This is the only situation we are allowed use this function
    // to allow nested calls to `run_with_bumps`/`render_on_display`,
    // because after the error message is displayed, the application will
    // shut down.
    unsafe { shape::unlock_bumps_on_failure() };

    ModelUI::screen_fatal_error(
        title.as_ascii_str().unwrap_or_default(),
        msg.as_ascii_str().unwrap_or_default(),
        footer.as_ascii_str().unwrap_or_default(),
    );
    ModelUI::backlight_on();
}

#[no_mangle]
extern "C" fn screen_boot_stage_2(fade_in: bool) {
    ModelUI::screen_boot_stage_2(fade_in);
}

#[no_mangle]
extern "C" fn screen_update() {
    ModelUI::screen_update();
}

#[no_mangle]
#[cfg(feature = "ui_debug")]
extern "C" fn disable_animation(disable: bool) {
    set_animation_disabled(disable);
}

#[no_mangle]
#[cfg(not(feature = "ui_debug"))]
extern "C" fn disable_animation(_disable: bool) {}
