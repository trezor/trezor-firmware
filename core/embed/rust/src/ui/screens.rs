//! Reexporting the `screens` module according to the
//! current feature (Trezor model)

#[cfg(all(feature = "model_tr", not(feature = "model_tt")))]
pub use super::model_tr::screens::*;
#[cfg(feature = "model_tt")]
pub use super::model_tt::screens::*;
use crate::ui::util::from_c_str;

#[no_mangle]
extern "C" fn screen_fatal_error_rust(
    title: *const cty::c_char,
    msg: *const cty::c_char,
    footer: *const cty::c_char,
) {
    let title = unsafe { from_c_str(title) }.unwrap_or("");
    let msg = unsafe { from_c_str(msg) }.unwrap_or("");
    let footer = unsafe { from_c_str(footer) }.unwrap_or("");

    screen_fatal_error(title, msg, footer);
}
