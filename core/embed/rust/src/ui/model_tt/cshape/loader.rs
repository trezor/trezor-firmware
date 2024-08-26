use crate::ui::{constant, display::Color, geometry::Point, shape, shape::Renderer};

pub enum LoaderRange {
    Full,
    FromTo(f32, f32),
}

pub fn render_loader<'s>(
    center: Point,
    inactive_color: Color,
    active_color: Color,
    background_color: Color,
    range: LoaderRange,
    target: &mut impl Renderer<'s>,
) {
    shape::Circle::new(center, constant::LOADER_OUTER)
        .with_bg(inactive_color)
        .render(target);

    match range {
        LoaderRange::Full => {
            shape::Circle::new(center, constant::LOADER_OUTER)
                .with_bg(active_color)
                .render(target);
        }
        LoaderRange::FromTo(start, end) => {
            shape::Circle::new(center, constant::LOADER_OUTER)
                .with_bg(active_color)
                .with_start_angle(start)
                .with_end_angle(end)
                .render(target);
        }
    }

    shape::Circle::new(center, constant::LOADER_INNER + 2)
        .with_bg(active_color)
        .render(target);

    shape::Circle::new(center, constant::LOADER_INNER)
        .with_bg(background_color)
        .render(target);
}
