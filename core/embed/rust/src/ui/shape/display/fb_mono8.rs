use crate::{
    trezorhal::display::{self, XFrameBuffer},
    ui::{
        display::Color,
        geometry::Offset,
        shape::{
            render::ScopedRenderer, BasicCanvas, DirectRenderer, DrawingCache, Mono8Canvas,
            Viewport,
        },
    },
};

use super::bumps::Bumps;

pub type ConcreteRenderer<'a, 'alloc> = DirectRenderer<'a, 'alloc, Mono8Canvas<'alloc>>;

/// Creates the `Renderer` object for drawing on a display and invokes a
/// user-defined function that takes a single argument `target`. The user's
/// function can utilize the `target` for drawing on the display.
///
/// `clip` specifies a rectangle area that the user will draw to.
/// If no clip is specified, the entire display area is used.
///
/// `bg_color` specifies a background color with which the clip is filled before
/// the drawing starts. If the background color is None, the background
/// is undefined, and the user has to fill it themselves.
pub fn render_on_display<'env, F>(viewport: Option<Viewport>, bg_color: Option<Color>, func: F)
where
    F: for<'alloc> FnOnce(&mut ScopedRenderer<'alloc, 'env, ConcreteRenderer<'_, 'alloc>>),
{
    let mut fb = XFrameBuffer::lock();
    let bumps = Bumps::lock();

    let width = display::DISPLAY_RESX as i16;
    let height = display::DISPLAY_RESY as i16;

    let cache = DrawingCache::new(&bumps);

    let mut canvas = unwrap!(Mono8Canvas::new(
        Offset::new(width, height),
        Some(fb.stride()),
        None,
        fb.buf()
    ));

    if let Some(viewport) = viewport {
        canvas.set_viewport(viewport);
    }

    let mut target = ScopedRenderer::new(DirectRenderer::new(&mut canvas, bg_color, &cache));

    func(&mut target);
}
