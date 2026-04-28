use super::super::theme;
use crate::ui::display::Color;
use crate::ui::geometry::Point;
use crate::ui::shape::{self, Renderer};

// outer circle
pub const INDICATOR_OUTER_RADIUS: i16 = 10;
const INDICATOR_OUTER_COLOR: Color = theme::GREEN_BRIGHT;

pub fn render_connected_indicator<'s>(point: Point, target: &mut impl Renderer<'s>) {
    shape::Circle::new(point, INDICATOR_OUTER_RADIUS)
        .with_fg(INDICATOR_OUTER_COLOR)
        .with_bg(INDICATOR_OUTER_COLOR)
        .render(target);
}
