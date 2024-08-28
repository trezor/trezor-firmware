use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
};

use super::{Canvas, DrawingCache, Shape, ShapeClone, Viewport};

// ==========================================================================
// trait Renderer
// ==========================================================================

/// All renders must implement Renderer trait
/// Renderers can immediately use the draw() method of the passed shape or
/// may store it (using the boxed() method) and draw it later
pub trait Renderer<'a> {
    fn viewport(&self) -> Viewport;

    fn set_viewport(&mut self, viewport: Viewport);

    fn set_window(&mut self, window: Rect) -> Viewport {
        let viewport = self.viewport();
        self.set_viewport(viewport.relative_window(window));
        viewport
    }

    fn set_clip(&mut self, clip: Rect) -> Viewport {
        let viewport = self.viewport();
        self.set_viewport(viewport.relative_clip(clip));
        viewport
    }

    fn render_shape<S>(&mut self, shape: S)
    where
        S: Shape<'a> + ShapeClone<'a>;

    fn in_window(&mut self, r: Rect, inner: &dyn Fn(&mut Self)) {
        let original = self.set_window(r);
        inner(self);
        self.set_viewport(original);
    }

    fn in_clip(&mut self, r: Rect, inner: &dyn Fn(&mut Self)) {
        let original = self.set_clip(r);
        inner(self);
        self.set_viewport(original);
    }

    fn with_origin(&mut self, origin: Offset, inner: &dyn Fn(&mut Self)) {
        let original = self.viewport();
        self.set_viewport(self.viewport().with_origin(origin));
        inner(self);
        self.set_viewport(original);
    }
}

// ==========================================================================
// struct DirectRenderer
// ==========================================================================

/// A simple implementation of a Renderer that draws directly onto the CanvasEx
pub struct DirectRenderer<'canvas, 'alloc, C>
where
    C: Canvas,
{
    /// Target canvas
    canvas: &'canvas mut C,
    /// Drawing cache (decompression context, scratch-pad memory)
    cache: DrawingCache<'alloc>,
}

impl<'canvas, 'alloc, C> DirectRenderer<'canvas, 'alloc, C>
where
    C: Canvas,
{
    /// Creates a new DirectRenderer instance with the given canvas
    pub fn new(
        canvas: &'canvas mut C,
        bg_color: Option<Color>,
        cache: DrawingCache<'alloc>,
    ) -> Self {
        if let Some(color) = bg_color {
            canvas.fill_background(color);
        }

        // TODO: consider storing original canvas.viewport
        //       and restoring it by drop() function

        Self { canvas, cache }
    }
}

impl<'canvas, 'alloc, C> Renderer<'alloc> for DirectRenderer<'canvas, 'alloc, C>
where
    C: Canvas,
{
    fn viewport(&self) -> Viewport {
        self.canvas.viewport()
    }

    fn set_viewport(&mut self, viewport: Viewport) {
        self.canvas.set_viewport(viewport);
    }

    fn render_shape<S>(&mut self, mut shape: S)
    where
        S: Shape<'alloc> + ShapeClone<'alloc>,
    {
        if self.canvas.viewport().contains(shape.bounds()) {
            shape.draw(self.canvas, &self.cache);
            shape.cleanup(&self.cache);
        }
    }
}
