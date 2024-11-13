use crate::ui::geometry::{Offset, Point, Rect};

use crate::trezorhal::display::{DISPLAY_RESX, DISPLAY_RESY};

pub const WIDTH: i16 = DISPLAY_RESX as _;
pub const HEIGHT: i16 = DISPLAY_RESY as _;
pub const LINE_SPACE: i16 = 4;
pub const FONT_BPP: i16 = 4;

pub const LOADER_OUTER: i16 = 59;

pub const LOADER_INNER: i16 = 42;

pub const LOADER_ICON_MAX_SIZE: i16 = 64;

pub const fn size() -> Offset {
    Offset::new(WIDTH, HEIGHT)
}
pub const SIZE: Offset = size();

pub const fn screen() -> Rect {
    Rect::from_top_left_and_size(Point::zero(), SIZE)
}
pub const SCREEN: Rect = screen();
