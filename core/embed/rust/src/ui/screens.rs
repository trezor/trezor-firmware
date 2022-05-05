//! Reexporting the `screens` module according to the
//! current feature (Trezor model)

#[cfg(all(feature = "model_tr", not(feature = "model_tt")))]
pub use super::model_tr::screens::*;
#[cfg(feature = "model_tt")]
pub use super::model_tt::screens::*;
use crate::ui::util::from_c_str;

#[no_mangle]
extern "C" fn screen_fatal_error_c(msg: *const cty::c_char, file: *const cty::c_char) {
    let msg = if msg.is_null() {
        None
    } else {
        unsafe { from_c_str(msg) }
    };
    let file = if file.is_null() {
        ""
    } else {
        unwrap!(unsafe { from_c_str(file) })
    };

    screen_fatal_error(msg, file);
}

#[no_mangle]
extern "C" fn screen_error_shutdown_c(msg: *const cty::c_char, file: *const cty::c_char) {
    let msg = if msg.is_null() {
        None
    } else {
        unsafe { from_c_str(msg) }
    };
    let file = if file.is_null() {
        ""
    } else {
        unwrap!(unsafe { from_c_str(file) })
    };

    screen_fatal_error(msg, file);
}
