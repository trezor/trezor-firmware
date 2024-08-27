use crate::{
    trezorhal::{
        bitblt::{BitBltCopy, BitBltFill},
        display,
    },
    ui::{
        display::Color,
        geometry::{Offset, Rect},
        shape::render::ScopedRenderer,
    },
};

use super::{
    super::{BasicCanvas, BitmapView, DrawingCache, ProgressiveRenderer, Viewport},
    base::Display,
    bumps,
};

use static_alloc::Bump;

pub struct NoFbRgb565;

impl Display for NoFbRgb565 {
    type Canvas<'canvas> = DisplayCanvas;

    type Renderer<'env, 'canvas, 'bump> = ProgressiveRenderer<'env, 'bump, Bump<[u8; bumps::BUMP_NODMA_SIZE]>, DisplayCanvas>
    where
        'canvas: 'env;

    fn display_canvas<'canvas, 'fb>(
        _framebuffer: &'canvas mut display::XFrameBuffer<'fb>,
    ) -> Self::Canvas<'canvas> {
        DisplayCanvas::new()
    }

    fn renderer<'env, 'canvas, 'bumps>(
        bumps: &'bumps bumps::Bumps<'bumps>,
        canvas: &'env mut Self::Canvas<'canvas>,
        bg_color: Color,
    ) -> Self::Renderer<'env, 'canvas, 'bumps>
    where
        'canvas: 'env,
    {
        let cache = DrawingCache::new(bumps);
        ProgressiveRenderer::new(
            canvas,
            Some(bg_color),
            cache,
            bumps.nodma,
            bumps::SHAPE_MAX_COUNT,
        )
    }
}

pub type ConcreteRenderer<'a, 'alloc> =
    ProgressiveRenderer<'a, 'alloc, Bump<[u8; bumps::BUMP_NODMA_SIZE]>, DisplayCanvas>;

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
    let bumps = bumps::Bumps::lock();

    let cache = DrawingCache::new(&bumps);
    let mut canvas = DisplayCanvas::new();

    if let Some(viewport) = viewport {
        canvas.set_viewport(viewport);
    }

    let mut target = ScopedRenderer::new(ProgressiveRenderer::new(
        &mut canvas,
        bg_color,
        cache,
        bumps.nodma,
        bumps::SHAPE_MAX_COUNT,
    ));

    func(&mut target);

    target.into_inner().render(16);
}

/// A simple display canvas allowing just two bitblt operations:
/// 'fill_rect' and 'draw_bitmap` needed by `ProgressiveRenderer`.
pub struct DisplayCanvas {
    size: Offset,
    viewport: Viewport,
}

impl DisplayCanvas {
    pub fn new() -> Self {
        let size = Offset::new(display::DISPLAY_RESX as i16, display::DISPLAY_RESY as i16);
        let viewport = Viewport::from_size(size);
        Self { size, viewport }
    }
}

impl BasicCanvas for DisplayCanvas {
    fn viewport(&self) -> Viewport {
        self.viewport
    }

    fn set_viewport(&mut self, viewport: Viewport) {
        self.viewport = viewport.absolute_clip(self.bounds());
    }

    fn size(&self) -> Offset {
        self.size
    }

    fn fill_rect(&mut self, r: Rect, color: Color, _alpha: u8) {
        let r = r.translate(self.viewport.origin);
        if let Some(bitblt) = BitBltFill::new(r, self.viewport.clip, color, 255) {
            bitblt.display_fill();
        }
    }

    fn draw_bitmap(&mut self, r: Rect, bitmap: BitmapView) {
        let r = r.translate(self.viewport.origin);
        if let Some(bitblt) = BitBltCopy::new(r, self.viewport.clip, &bitmap) {
            bitblt.display_copy();
        }
    }
}
