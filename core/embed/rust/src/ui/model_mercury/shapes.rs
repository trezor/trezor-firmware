use crate::ui::{display::Color, geometry::Point, model_mercury::constant, shape, shape::Renderer};

pub fn render_loader<'s>(
    center: Point,
    inactive_color: Color,
    active_color: Color,
    background_color: Color,
    start: i16,
    end: i16,
    full: bool,
    target: &mut impl Renderer<'s>,
) {
    shape::Circle::new(center, constant::LOADER_OUTER)
        .with_bg(inactive_color)
        .render(target);

    if full {
        shape::Circle::new(center, constant::LOADER_OUTER)
            .with_bg(active_color)
            .render(target);
    } else {
        shape::Circle::new(center, constant::LOADER_OUTER)
            .with_bg(active_color)
            .with_start_angle(start)
            .with_end_angle(end)
            .render(target);
    }

    shape::Circle::new(center, constant::LOADER_INNER + 2)
        .with_bg(background_color)
        .render(target);
}
