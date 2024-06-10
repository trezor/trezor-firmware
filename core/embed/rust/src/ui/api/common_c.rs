//! Reexporting the `screens` module according to the
//! current feature (Trezor model)

use crate::ui::ui_features::{ModelUI, UIFeaturesCommon};

#[cfg(not(feature = "new_rendering"))]
use crate::ui::{
    component::image::Image,
    display::{Color, Icon},
    geometry::{Alignment2D, Point},
};

use crate::{trezorhal::fatal_error, ui::util::from_c_str};

#[no_mangle]
extern "C" fn error_shutdown_rust(
    title: *const cty::c_char,
    msg: *const cty::c_char,
    footer: *const cty::c_char,
) -> ! {
    let title = unsafe { from_c_str(title) }.unwrap_or("");
    let msg = unsafe { from_c_str(msg) }.unwrap_or("");
    let footer = unsafe { from_c_str(footer) }.unwrap_or("");

    fatal_error::error_shutdown(title, msg, footer)
}

#[no_mangle]
extern "C" fn screen_boot_stage_2() {
    ModelUI::screen_boot_stage_2();
}

#[no_mangle]
#[cfg(not(feature = "new_rendering"))]
extern "C" fn display_icon(
    x: cty::int16_t,
    y: cty::int16_t,
    data: *const cty::uint8_t,
    data_len: cty::uint32_t,
    fg_color: cty::uint16_t,
    bg_color: cty::uint16_t,
) {
    let data_slice = unsafe { core::slice::from_raw_parts(data, data_len as usize) };
    let icon = Icon::new(data_slice);
    icon.draw(
        Point::new(x, y),
        Alignment2D::TOP_LEFT,
        Color::from_u16(fg_color),
        Color::from_u16(bg_color),
    );
}

#[no_mangle]
#[cfg(not(feature = "new_rendering"))]
extern "C" fn display_image(
    x: cty::int16_t,
    y: cty::int16_t,
    data: *const cty::uint8_t,
    data_len: cty::uint32_t,
) {
    let data_slice = unsafe { core::slice::from_raw_parts(data, data_len as usize) };
    let image = Image::new(data_slice);
    image.draw(Point::new(x, y), Alignment2D::TOP_LEFT);
}
