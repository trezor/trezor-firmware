use crate::ui::{
    display::Color,
    geometry::{Offset, Point, Rect},
    shape::{self, Renderer},
};

use super::super::theme;

// outer circle
pub const INDICATOR_OUTER_RADIUS: i16 = 10;
const INDICATOR_OUTER_COLOR: Color = theme::GREEN_BRIGHT;

// inner rectangle
const INDICATOR_INNER_SIZE: i16 = 9;
const INDICATOR_INNER_COLOR: Color = theme::GREEN;

pub fn render_connected_indicator<'s>(point: Point, target: &mut impl Renderer<'s>) {
    shape::Circle::new(point, INDICATOR_OUTER_RADIUS)
        .with_fg(INDICATOR_OUTER_COLOR)
        .with_bg(INDICATOR_OUTER_COLOR)
        .render(target);
    shape::Bar::new(Rect::snap(
        point,
        Offset::uniform(INDICATOR_INNER_SIZE),
        Alignment2D::CENTER,
    ))
    .with_fg(INDICATOR_INNER_COLOR)
    .with_bg(INDICATOR_INNER_COLOR)
    .with_radius(1)
    .render(target);
}
