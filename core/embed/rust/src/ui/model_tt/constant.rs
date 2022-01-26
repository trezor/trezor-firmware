use crate::ui::geometry::{Offset, Point, Rect};

pub const WIDTH: i32 = 240;
pub const HEIGHT: i32 = 240;
pub const LINE_SPACE: i32 = 4;

pub fn size() -> Offset {
    Offset::new(WIDTH, HEIGHT)
}

pub fn screen() -> Rect {
    Rect::from_top_left_and_size(Point::zero(), size())
}
