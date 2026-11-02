use crate::ui::display::Color;
use crate::ui::shape::render::ScopedRenderer;
use crate::ui::shape::{DirectRenderer, Mono8Canvas, Viewport};

pub type ConcreteRenderer<'a, 'alloc> = DirectRenderer<'a, 'alloc, Mono8Canvas<'alloc>>;

/// Headless models have no framebuffer, so rendering is a no-op: the render
/// closure is not invoked and the requested UI is discarded. This keeps the
/// boot chain running instead of panicking, consistent with the display_none
/// driver whose operations are no-ops as well.
pub fn render_on_display<'env, F>(_viewport: Option<Viewport>, _bg_color: Option<Color>, _func: F)
where
    F: for<'alloc> FnOnce(&mut ScopedRenderer<'alloc, 'env, ConcreteRenderer<'_, 'alloc>>),
{
}
