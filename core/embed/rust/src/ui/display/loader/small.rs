use crate::ui::{
    constant::screen,
    display::{rect_fill, Color},
    geometry::{Offset, Point, Rect},
};
use core::f32::consts::SQRT_2;

const STAR_COUNT: usize = 8;
const RADIUS: i16 = 3;
const DIAGONAL: i16 = ((RADIUS as f32 * SQRT_2) / 2_f32) as i16;
const LOADER_SIZE: Offset = Offset::uniform(2 * RADIUS + 3);

fn fill_point(point: Point, color: Color) {
    let area = Rect::from_center_and_size(point, Offset::uniform(1));
    rect_fill(area, color);
}

pub fn loader_small_indeterminate(progress: u16, y_offset: i16, fg_color: Color, bg_color: Color) {
    let area =
        Rect::from_center_and_size(screen().center(), LOADER_SIZE).translate(Offset::y(y_offset));

    rect_fill(area, bg_color);

    // Offset of the normal point and then the extra offset for the main point
    let offsets: [(Offset, Offset); STAR_COUNT] = [
        (Offset::y(-RADIUS), Offset::y(-1)),
        (Offset::new(DIAGONAL, -DIAGONAL), Offset::new(1, -1)),
        (Offset::x(RADIUS), Offset::x(1)),
        (Offset::new(DIAGONAL, DIAGONAL), Offset::new(1, 1)),
        (Offset::y(RADIUS), Offset::y(1)),
        (Offset::new(-DIAGONAL, DIAGONAL), Offset::new(-1, 1)),
        (Offset::x(-RADIUS), Offset::x(-1)),
        (Offset::new(-DIAGONAL, -DIAGONAL), Offset::new(-1, -1)),
    ];

    let main_idx = (STAR_COUNT * progress as usize / 1000) % STAR_COUNT;

    for (i, (point_offset, main_offset)) in offsets.iter().enumerate() {
        // Skip it when it is behind the main one (clockwise)
        if (main_idx + 1) % STAR_COUNT == i {
            continue;
        }

        // Draw the normal point
        let point = area.center() + *point_offset;
        fill_point(point, fg_color);

        // Draw the main point
        if main_idx == i {
            fill_point(point + *main_offset, fg_color);
        }
    }
}
