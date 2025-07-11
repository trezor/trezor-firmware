use crate::ui::{
    display::Color,
    geometry::{Axis, Point, Rect},
    lerp::Lerp,
    shape::{self, Renderer},
};

use super::super::theme;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Gradient {
    DefaultGrey,
    #[cfg(feature = "micropython")]
    SignGreen,
    #[cfg(feature = "micropython")]
    Warning,
    #[cfg(feature = "micropython")]
    Alert,
    #[cfg(feature = "micropython")]
    HomescreenBase,
    #[cfg(feature = "micropython")]
    HomescreenLEDSim(Color),
}

impl Gradient {
    /// Renders a gradient within the given rectangle
    ///
    /// # Arguments
    /// * `target` - The renderer to draw to
    /// * `area` - The rectangle to fill with gradient
    /// * `step_size` - Step size for speed tuning (1 = full quality, higher =
    ///   faster but lower quality)
    pub fn render<'s>(&self, target: &mut impl Renderer<'s>, area: Rect, step_size: u16) {
        render_gradient(target, area, *self, step_size);
    }
}

fn render_gradient<'s>(
    target: &mut impl Renderer<'s>,
    area: Rect,
    gradient_type: Gradient,
    step_size: u16,
) {
    match gradient_type {
        Gradient::DefaultGrey => render_default_grey(target, area, step_size),
        #[cfg(feature = "micropython")]
        Gradient::SignGreen => render_sign_green(target, area, step_size),
        #[cfg(feature = "micropython")]
        Gradient::Warning => render_warning(target, area, step_size),
        #[cfg(feature = "micropython")]
        Gradient::Alert => render_alert(target, area, step_size),
        #[cfg(feature = "micropython")]
        Gradient::HomescreenBase => render_homescreen_base(target, area, step_size),
        #[cfg(feature = "micropython")]
        Gradient::HomescreenLEDSim(color) => render_led_simulation(target, area, step_size, color),
    }
}

fn render_default_grey<'s>(target: &mut impl Renderer<'s>, area: Rect, step_size: u16) {
    // Layer 1: Vertical Gradient (Overall intensity: 100%)
    // Stops:    21%, 100%
    // Opacity: 100%, 20%
    // Color: color1, color2
    let color1 = theme::GREY_EXTRA_DARK;
    let color2 = theme::GREEN_DARK;
    for (slice, factor) in iter_slices(area, Axis::Vertical, step_size) {
        let factor = normalize_factor(factor, 0.21, 1.00);
        let color = Color::lerp(color1, color2, factor);
        let alpha = u8::lerp(u8::MAX, 51, factor);
        shape::Bar::new(slice)
            .with_bg(color)
            .with_alpha(alpha)
            .render(target);
    }
    render_edge_fade(target, area, theme::BLACK, step_size);
    render_black_overlay(target, area);
}

#[cfg(feature = "micropython")]
fn render_sign_green<'s>(target: &mut impl Renderer<'s>, area: Rect, step_size: u16) {
    // Layer 1: Vertical Gradient (Overall intensity: 100%)
    // Stops:    21%, 100%
    // Opacity: 100%,  20%
    for (slice, factor) in iter_slices(area, Axis::Vertical, step_size) {
        let factor = normalize_factor(factor, 0.21, 1.00);
        let alpha = u8::lerp(u8::MAX, 51, factor);
        shape::Bar::new(slice)
            .with_bg(theme::GREEN_DARK)
            .with_alpha(alpha)
            .render(target);
    }

    render_edge_fade(target, area, theme::BLACK, step_size);
    render_black_overlay(target, area);
}

#[cfg(feature = "micropython")]
fn render_warning<'s>(target: &mut impl Renderer<'s>, area: Rect, step_size: u16) {
    // Layer 1: Vertical Gradient (Overall intensity: 100%)
    // Stops:    21%, 100%
    // Opacity: 100%,  20%
    for (slice, factor) in iter_slices(area, Axis::Vertical, step_size) {
        let factor = normalize_factor(factor, 0.21, 1.00);
        let alpha = u8::lerp(u8::MAX, 51, factor);
        shape::Bar::new(slice)
            .with_bg(theme::YELLOW_DARK)
            .with_alpha(alpha)
            .render(target);
    }

    render_edge_fade(target, area, theme::YELLOW_DARK, step_size);
    render_black_overlay(target, area);
}

#[cfg(feature = "micropython")]
fn render_alert<'s>(target: &mut impl Renderer<'s>, area: Rect, step_size: u16) {
    render_alert_horizontal(target, area, theme::ORANGE_SUPER_DARK, step_size);
    // Layer 2 Vertical Gradient (Overall intensity: 100%)
    // Stops:   85%,  100%
    // Opacity: 20%,  100%
    let color1 = theme::ORANGE_SUPER_DARK;
    let color2 = theme::BLACK;
    for (slice, factor) in iter_slices(area, Axis::Vertical, step_size) {
        let factor = normalize_factor(factor, 0.80, 1.00);
        let alpha = u8::lerp(51, u8::MAX, factor);
        let color = Color::lerp(color1, color2, factor);
        shape::Bar::new(slice)
            .with_bg(color)
            .with_alpha(alpha)
            .render(target);
    }
    render_black_overlay(target, area);
}

#[cfg(feature = "micropython")]
fn render_homescreen_base<'s>(target: &mut impl Renderer<'s>, area: Rect, step_size: u16) {
    for (slice, factor) in iter_slices(area, Axis::Vertical, step_size) {
        shape::Bar::new(slice)
            .with_bg(theme::BG)
            .with_alpha(u8::lerp(u8::MIN, u8::MAX, factor))
            .render(target);
    }
}

#[cfg(feature = "micropython")]
fn render_led_simulation<'a>(
    target: &mut impl Renderer<'a>,
    area: Rect,
    step_size: u16,
    color: Color,
) {
    // Vertical gradient (color intensity fading from bottom to top)
    for (slice, factor) in iter_slices(area, Axis::Vertical, step_size) {
        // Gradient 1 (Overall intensity: 35%)
        // Stops:     0%,  40%
        // Opacity: 100%,  20%
        let factor_grad_1 = (factor / 0.4).clamp(0.2, 1.0);

        shape::Bar::new(slice)
            .with_bg(color)
            .with_alpha(u8::lerp(89, u8::MIN, factor_grad_1))
            .render(target);

        // Gradient 2 (Overall intensity: 70%)
        // Stops:     2%, 63%
        // Opacity: 100%,  0%
        let factor_grad_2 = normalize_factor(factor, 0.02, 0.63);
        let alpha = u8::lerp(179, u8::MIN, factor_grad_2);
        shape::Bar::new(slice)
            .with_bg(color)
            .with_alpha(alpha)
            .render(target);
    }

    // Horizontal gradient (transparency increasing toward center)
    for (slice, _) in iter_slices(area, Axis::Horizontal, step_size) {
        // Calculate distance from center as a normalized factor (0 at center, 1 at
        // edges)
        let x_mid = area.center().x;
        let x_half_width = (area.width() / 2) as f32;
        let dist_from_mid = (slice.x0 - x_mid).abs() as f32 / x_half_width;

        shape::Bar::new(slice)
            .with_bg(theme::BG)
            .with_alpha(u8::lerp(u8::MIN, u8::MAX, dist_from_mid))
            .render(target);
    }
}

fn render_edge_fade<'s>(
    target: &mut impl Renderer<'s>,
    area: Rect,
    color_mid: Color,
    step_size: u16,
) {
    // Render horizontal distance-from-mid gradient
    // Black at edges, color_mid at center with minimal opacity
    let x_mid = area.center().x;
    let half_width = (area.width() / 2) as f32;
    for (slice, _) in iter_slices(area, Axis::Horizontal, step_size) {
        let dist_from_mid = (slice.x0 - x_mid).abs() as f32 / half_width;
        let alpha = u8::lerp(u8::MIN, u8::MAX, dist_from_mid);
        let color = Color::lerp(color_mid, theme::BLACK, dist_from_mid);
        shape::Bar::new(slice)
            .with_bg(color)
            .with_alpha(alpha)
            .render(target);
    }
}

fn render_alert_horizontal<'s>(
    target: &mut impl Renderer<'s>,
    area: Rect,
    color_mid: Color,
    step_size: u16,
) {
    // Render horizontal distance-from-mid gradient
    // Black at edges, color_mid at center with full opacity
    let x_mid = area.center().x;
    let half_width = (area.width() / 2) as f32;
    for (slice, _) in iter_slices(area, Axis::Horizontal, step_size) {
        let dist_from_mid = (slice.x0 - x_mid).abs() as f32 / half_width;
        let color = Color::lerp(color_mid, theme::BLACK, dist_from_mid);
        shape::Bar::new(slice)
            .with_bg(color)
            .with_alpha(u8::MAX)
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

// Helper functions

/// Normalizes a factor to the given range and clamps it to [0.0, 1.0]
fn normalize_factor(factor: f32, start: f32, end: f32) -> f32 {
    ((factor - start) / (end - start)).clamp(0.0, 1.0)
}

fn iter_slices(area: Rect, axis: Axis, step_size: u16) -> impl Iterator<Item = (Rect, f32)> {
    let (start, end) = match axis {
        Axis::Horizontal => (area.x0, area.x1),
        Axis::Vertical => (area.y0, area.y1),
    };

    let total_length = end - start;

    (start..end).step_by(step_size as usize).map(move |pos| {
        let remaining = end - pos;
        let slice_size = (step_size as i16).min(remaining);
        let slice = match axis {
            Axis::Horizontal => Rect::new(
                Point::new(pos, area.y0),
                Point::new(pos + slice_size, area.y1),
            ),
            Axis::Vertical => Rect::new(
                Point::new(area.x0, pos),
                Point::new(area.x1, pos + slice_size),
            ),
        };

        // Calculate factor based on the center of the slice for better visual accuracy
        let slice_center = pos + slice_size / 2;
        let factor = (slice_center - start) as f32 / total_length as f32;
        (slice, factor)
    })
}
