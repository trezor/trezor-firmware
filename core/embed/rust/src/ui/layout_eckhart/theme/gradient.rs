use crate::ui::{
    display::Color,
    geometry::{Point, Rect},
    lerp::Lerp,
    shape::{self, Renderer},
};

use super::super::theme;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Gradient {
    DefaultGrey,
    SignGreen,
    Warning,
    Alert,
}

impl Gradient {
    /// Renders a gradient within the given rectangle
    ///
    /// # Arguments
    /// * `target` - The renderer to draw to
    /// * `area` - The rectangle to fill with gradient
    /// * `step_size` - Step size for speed tuning (1 = full quality, higher =
    ///   faster but lower quality)
    pub fn render<'s>(&self, target: &mut impl Renderer<'s>, area: Rect, step_size: i16) {
        render_gradient(target, area, *self, step_size);
    }
}

fn render_gradient<'s>(
    target: &mut impl Renderer<'s>,
    area: Rect,
    gradient_type: Gradient,
    step_size: i16,
) {
    match gradient_type {
        Gradient::DefaultGrey => render_default_grey(target, area, step_size),
        Gradient::SignGreen => render_sign_green(target, area, step_size),
        Gradient::Warning => render_warning(target, area, step_size),
        Gradient::Alert => render_alert(target, area, step_size),
    }
}

fn render_default_grey<'s>(target: &mut impl Renderer<'s>, area: Rect, step_size: i16) {
    let height = area.height();

    // Layer 1: Vertical Gradient (Overall intensity: 100%)
    // Stops:    21%, 100%
    // Opacity: 100%, 20%
    // Color: color1, color2
    let color1 = theme::GREY_EXTRA_DARK;
    let color2 = theme::GREEN_DARK;
    for y in (area.y0..area.y1).step_by(step_size as usize) {
        let slice_height = (step_size.min(area.y1 - y)).max(1);
        let slice = Rect::new(
            Point::new(area.x0, y),
            Point::new(area.x1, y + slice_height),
        );
        let factor = (y - area.y0) as f32 / height as f32;
        let factor = normalize_factor(factor, 0.21, 1.00);
        let color = Color::lerp(color1, color2, factor);
        let alpha = u8::lerp(u8::MAX, 51, factor);
        shape::Bar::new(slice)
            .with_bg(color)
            .with_alpha(alpha)
            .render(target);
    }

    render_horizontal_gradient(target, area, theme::BLACK, step_size);
    render_black_overlay(target, area);
}

fn render_sign_green<'s>(target: &mut impl Renderer<'s>, area: Rect, step_size: i16) {
    let height = area.height();

    // Layer 1: Vertical Gradient (Overall intensity: 100%)
    // Stops:    21%, 100%
    // Opacity: 100%,  20%
    for y in (area.y0..area.y1).step_by(step_size as usize) {
        let slice_height = (step_size.min(area.y1 - y)).max(1);
        let slice = Rect::new(
            Point::new(area.x0, y),
            Point::new(area.x1, y + slice_height),
        );
        let factor = (y - area.y0) as f32 / height as f32;
        let factor = normalize_factor(factor, 0.21, 1.00);
        let alpha = u8::lerp(u8::MAX, 51, factor);
        shape::Bar::new(slice)
            .with_bg(theme::GREEN_DARK)
            .with_alpha(alpha)
            .render(target);
    }

    render_horizontal_gradient(target, area, theme::BLACK, step_size);
    render_black_overlay(target, area);
}

fn render_warning<'s>(target: &mut impl Renderer<'s>, area: Rect, step_size: i16) {
    let height = area.height();

    // Layer 1: Vertical Gradient (Overall intensity: 100%)
    // Stops:    21%, 100%
    // Opacity: 100%,  20%
    for y in (area.y0..area.y1).step_by(step_size as usize) {
        let slice_height = (step_size.min(area.y1 - y)).max(1);
        let slice = Rect::new(
            Point::new(area.x0, y),
            Point::new(area.x1, y + slice_height),
        );
        let factor = (y - area.y0) as f32 / height as f32;
        let factor = normalize_factor(factor, 0.21, 1.00);
        let alpha = u8::lerp(u8::MAX, 51, factor);
        shape::Bar::new(slice)
            .with_bg(theme::YELLOW_DARK)
            .with_alpha(alpha)
            .render(target);
    }

    render_horizontal_gradient(target, area, theme::YELLOW_DARK, step_size);
    render_black_overlay(target, area);
}

fn render_alert<'s>(target: &mut impl Renderer<'s>, area: Rect, step_size: i16) {
    render_horizontal_gradient(target, area, theme::ORANGE_SUPER_DARK, step_size);

    // Layer 1: Vertical Gradient (Overall intensity: 100%)
    // Stops:   80%,  100%
    // Opacity: 20%,  100%
    let height = area.height();
    for y in (area.y0..area.y1).step_by(step_size as usize) {
        let slice_width = (step_size.min(area.y1 - y)).max(1);
        let slice = Rect::new(Point::new(area.x0, y), Point::new(area.x1, y + slice_width));
        let factor = (y - area.y0) as f32 / height as f32;
        let factor_grad = normalize_factor(factor, 0.80, 1.00);
        let alpha = u8::lerp(51, u8::MAX, factor_grad);
        shape::Bar::new(slice)
            .with_bg(theme::ORANGE_SUPER_DARK)
            .with_alpha(alpha)
            .render(target);
    }

    render_black_overlay(target, area);
}

// Helper functions

/// Normalizes a factor to the given range and clamps it to [0.0, 1.0]
fn normalize_factor(factor: f32, start: f32, end: f32) -> f32 {
    ((factor - start) / (end - start)).clamp(0.0, 1.0)
}

fn render_horizontal_gradient<'s>(
    target: &mut impl Renderer<'s>,
    area: Rect,
    color_mid: Color,
    step_size: i16,
) {
    // Render horizontal distance-from-mid gradient
    // Black at edges, color_mid at center with minimal opacity
    let half_width = (area.width() / 2) as f32;
    let x_mid = area.center().x;
    for x in (area.x0..area.x1).step_by(step_size as usize) {
        let slice_width = (step_size.min(area.x1 - x)).max(1);
        let slice = Rect::new(Point::new(x, area.y0), Point::new(x + slice_width, area.y1));
        let dist_from_mid = (x - x_mid).abs() as f32 / half_width;
        let alpha = u8::lerp(u8::MIN, u8::MAX, dist_from_mid);
        let color = Color::lerp(color_mid, theme::BLACK, dist_from_mid);
        shape::Bar::new(slice)
            .with_bg(color)
            .with_alpha(alpha)
            .render(target);
    }
}

fn render_black_overlay<'s>(target: &mut impl Renderer<'s>, area: Rect) {
    // Render a black overlay (Overall intensity: 20%)
    shape::Bar::new(area)
        .with_bg(theme::BG)
        .with_alpha(51) // 20% opacity
        .render(target);
}
