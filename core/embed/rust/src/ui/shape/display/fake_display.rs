use crate::ui::display::Color;
use crate::ui::shape::render::ScopedRenderer;
use crate::ui::shape::{DirectRenderer, Mono8Canvas, Viewport};

pub type ConcreteRenderer<'a, 'alloc> = DirectRenderer<'a, 'alloc, Mono8Canvas<'alloc>>;

/// Headless (display-less) models have no framebuffer to render into, so drawing
/// is a no-op: the render closure is simply not invoked and the requested UI is
/// silently discarded. This keeps the boot chain running on "none" display
/// models (e.g. D003/D004) instead of panicking, consistent with the io/display_none
/// driver whose operations are also no-ops.
pub fn render_on_display<'env, F>(_viewport: Option<Viewport>, _bg_color: Option<Color>, _func: F)
where
    F: for<'alloc> FnOnce(&mut ScopedRenderer<'alloc, 'env, ConcreteRenderer<'_, 'alloc>>),
{
    // No display to render to; intentionally does nothing.
}


