mod circular;
#[cfg(feature = "dma2d")]
mod circular_thin;
mod rectangular;
mod small;
mod starry;

use crate::ui::display::{Color, Icon};

#[cfg(feature = "model_tt")]
use crate::ui::display::loader::circular::{
    loader_circular as determinate, loader_circular_indeterminate as indeterminate,
};
#[cfg(any(feature = "model_tt", feature = "model_mercury"))]
pub use crate::ui::display::loader::circular::{loader_circular_uncompress, LoaderDimensions};

#[cfg(all(feature = "model_mercury", not(feature = "model_tt")))]
use crate::ui::display::loader::circular_thin::{
    loader_circular as determinate, loader_circular_indeterminate as indeterminate,
};

#[cfg(all(not(feature = "model_tt"), not(feature = "model_mercury")))]
use crate::ui::display::loader::rectangular::loader_rectangular as determinate;
#[cfg(all(not(feature = "model_tt"), not(feature = "model_mercury")))]
use crate::ui::display::loader::starry::loader_starry_indeterminate as indeterminate;

pub use small::loader_small_indeterminate;

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
