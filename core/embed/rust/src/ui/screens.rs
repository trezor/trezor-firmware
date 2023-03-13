//! Reexporting the `screens` module according to the
//! current feature (Trezor model)

#[cfg(all(feature = "model_tr", not(feature = "model_tt")))]
pub use super::model_tr::screens::*;
#[cfg(feature = "model_tt")]
pub use super::model_tt::screens::*;
use crate::ui::util::from_c_str;

macro_rules! convert_str {
    ($str:expr) => {
        if ($str).is_null() {
            ""
        } else {
            unwrap!(unsafe { from_c_str($str) })
        }
    };
}

#[no_mangle]
extern "C" fn screen_fatal_error_rust(
    title: *const cty::c_char,
    msg: *const cty::c_char,
    footer: *const cty::c_char,
) {
    let title = convert_str!(title);
    let msg = convert_str!(msg);
    let footer = convert_str!(footer);

    screen_fatal_error(title, msg, footer);
}
