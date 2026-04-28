use crate::ui::{
    display::Color,
    geometry::Point,
    shape::{self, Renderer},
};

use super::super::theme;

// outer circle
pub const INDICATOR_OUTER_RADIUS: i16 = 10;
const INDICATOR_OUTER_COLOR: Color = theme::GREEN_BRIGHT;

pub fn render_connected_indicator<'s>(point: Point, target: &mut impl Renderer<'s>) {
    shape::Circle::new(point, INDICATOR_OUTER_RADIUS)
        .with_fg(INDICATOR_OUTER_COLOR)
        .with_bg(INDICATOR_OUTER_COLOR)
        .render(target);
}
