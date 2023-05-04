use crate::ui::geometry::{Offset, Point, Rect};

pub const WIDTH: i16 = 240;
pub const HEIGHT: i16 = 240;
pub const LINE_SPACE: i16 = 4;
pub const FONT_BPP: i16 = 4;

pub const LOADER_OUTER: i16 = 60;
pub const LOADER_INNER: i16 = 42;
pub const LOADER_ICON_MAX_SIZE: i16 = 64;

pub const fn size() -> Offset {
    Offset::new(WIDTH, HEIGHT)
}

pub const fn screen() -> Rect {
    Rect::from_top_left_and_size(Point::zero(), size())
}
