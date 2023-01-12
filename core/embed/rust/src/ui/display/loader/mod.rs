mod circular;
mod rectangular;
mod starry;

use crate::ui::display::{Color, Icon};
use core::slice::from_raw_parts;

#[cfg(feature = "model_tt")]
use crate::ui::display::loader::circular::{
    loader_circular as determinate, loader_circular_indeterminate as indeterminate,
};
#[cfg(not(feature = "model_tt"))]
use crate::ui::display::loader::rectangular::loader_rectangular as determinate;
#[cfg(not(feature = "model_tt"))]
use crate::ui::display::loader::starry::loader_starry_indeterminate as indeterminate;

pub const LOADER_MIN: u16 = 0;
pub const LOADER_MAX: u16 = 1000;

pub fn loader(
    progress: u16,
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(Icon, Color)>,
) {
    determinate(progress, y_offset, fg_color, bg_color, icon);
}

pub fn loader_indeterminate(
    progress: u16,
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(Icon, Color)>,
) {
    indeterminate(progress, y_offset, fg_color, bg_color, icon);
}

//TODO: remove when loader is no longer called from C
#[no_mangle]
pub extern "C" fn loader_uncompress_r(
    y_offset: cty::int32_t,
    fg_color: cty::uint16_t,
    bg_color: cty::uint16_t,
    icon_color: cty::uint16_t,
    progress: cty::int32_t,
    indeterminate: cty::int32_t,
    icon_data: cty::uintptr_t,
    icon_data_size: cty::uint32_t,
) {
    let fg = Color::from_u16(fg_color);
    let bg = Color::from_u16(bg_color);
    let ic_color = Color::from_u16(icon_color);

    let i = if icon_data != 0 {
        let data_slice = unsafe { from_raw_parts(icon_data as _, icon_data_size as _) };
        Some((Icon::new(data_slice), ic_color))
    } else {
        None
    };

    if indeterminate == 0 {
        loader(progress as _, y_offset as _, fg, bg, i);
    } else {
        loader_indeterminate(progress as _, y_offset as _, fg, bg, i);
    }
}
