use crate::ui::{
    display::Color,
    shape::{render::ScopedRenderer, Canvas, DirectRenderer, DrawingCache},
};

use super::bumps::Bumps;

/// Creates the `Renderer` object for drawing on a specified canvas and invokes
/// a user-defined function that takes a single argument `target`. The user's
/// function can utilize the `target` for drawing on the canvas.
///
/// `bg_color` specifies a background color with which the canvas is filled
/// before the drawing starts. If the background color is None, the background
/// is undefined, and the user has to fill it themselves.
pub fn render_on_canvas<'env, C: Canvas, F>(canvas: &mut C, bg_color: Option<Color>, func: F)
where
    F: for<'alloc> FnOnce(&mut ScopedRenderer<'alloc, 'env, DirectRenderer<'_, 'alloc, C>>),
{
    let bumps = Bumps::lock();
    let cache = DrawingCache::new(&bumps);
    let mut target = ScopedRenderer::new(DirectRenderer::new(canvas, bg_color, &cache));
    func(&mut target);
}
