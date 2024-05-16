use crate::ui::{
    display::Color,
    shape::{Canvas, DirectRenderer, DrawingCache},
};

use super::bumps::run_with_bumps;

/// Creates the `Renderer` object for drawing on a the specified and invokes a
/// user-defined function that takes a single argument `target`. The user's
/// function can utilize the `target` for drawing on the canvas.
///
/// `bg_color` specifies a background color with which the canvas is filled
/// before the drawing starts. If the background color is None, the background
/// is undefined, and the user has to fill it themselves.
pub fn render_on_canvas<'a, C: Canvas, F>(canvas: &mut C, bg_color: Option<Color>, func: F)
where
    F: FnOnce(&mut DirectRenderer<'_, 'a, C>),
{
    run_with_bumps(|bump_a, bump_b| {
        let cache = DrawingCache::new(bump_a, bump_b);
        let mut target = DirectRenderer::new(canvas, bg_color, &cache);
        func(&mut target);
    });
}
