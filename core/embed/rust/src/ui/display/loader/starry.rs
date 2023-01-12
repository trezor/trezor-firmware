use crate::ui::{
    constant::{screen, LOADER_OUTER},
    display::{rect_fill, rect_fill_rounded, rect_fill_rounded1, Color, Icon},
    geometry::{Offset, Point, Rect, CENTER},
};
use core::f32::consts::SQRT_2;

const SIZE_SMALL: i16 = 2;
const SIZE_MEDIUM: i16 = 4;
const SIZE_LARGE: i16 = 6;
const RADIUS: i16 = 13;
const DIAGONAL: i16 = ((RADIUS as f32 * SQRT_2) / 2_f32) as i16;

fn star_small(center: Point, fg: Color, _bg: Color) {
    let r = Rect::from_center_and_size(center, Offset::uniform(SIZE_SMALL));
    rect_fill(r, fg);
}

fn star_medium(center: Point, fg: Color, bg: Color) {
    let r = Rect::from_center_and_size(center, Offset::uniform(SIZE_MEDIUM));
    rect_fill_rounded1(r, fg, bg);
}

fn star_large(center: Point, fg: Color, bg: Color) {
    let r = Rect::from_center_and_size(center, Offset::uniform(SIZE_LARGE));
    rect_fill_rounded(r, fg, bg, 2);
}

pub fn loader_starry_indeterminate(
    progress: u16,
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(Icon, Color)>,
) {
    let area = Rect::from_center_and_size(screen().center(), Offset::uniform(LOADER_OUTER as _))
        .translate(Offset::y(y_offset));

    rect_fill(area, bg_color);

    let coords = [
        Point::new(area.center().x, area.center().y - RADIUS),
        Point::new(area.center().x + DIAGONAL, area.center().y - DIAGONAL),
        Point::new(area.center().x + RADIUS, area.center().y),
        Point::new(area.center().x + DIAGONAL, area.center().y + DIAGONAL),
        Point::new(area.center().x, area.center().y + RADIUS),
        Point::new(area.center().x - DIAGONAL, area.center().y + DIAGONAL),
        Point::new(area.center().x - RADIUS, area.center().y),
        Point::new(area.center().x - DIAGONAL, area.center().y - DIAGONAL),
    ];

    let big_idx = (progress / 125) as usize % 8;

    for (i, c) in coords.iter().enumerate() {
        if i == big_idx {
            star_large(*c, fg_color, bg_color);
        } else if (big_idx + 1) % 8 == i || (big_idx - 1) % 8 == i {
            star_medium(*c, fg_color, bg_color);
        } else {
            star_small(*c, fg_color, bg_color);
        }
    }

    if let Some((icon, color)) = icon {
        icon.draw(area.center(), CENTER, color, bg_color);
    }
}
