use crate::ui::geometry::{Offset, Point, Rect};

pub const WIDTH: i32 = 128;
pub const HEIGHT: i32 = 128;
pub const LINE_SPACE: i32 = 1;
pub const FONT_BPP: i32 = 1;

pub const LOADER_OUTER: f32 = 20_f32;
pub const LOADER_INNER: f32 = 14_f32;
pub const LOADER_ICON_MAX_SIZE: i32 = 24;

pub const fn size() -> Offset {
    Offset::new(WIDTH, HEIGHT)
}

pub const fn screen() -> Rect {
    Rect::from_top_left_and_size(Point::zero(), size())
}
