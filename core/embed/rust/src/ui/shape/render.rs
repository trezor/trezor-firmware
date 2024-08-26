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

    fn with_translate(&mut self, offset: Offset, inner: &dyn Fn(&mut Self)) {
        let original = self.viewport();
        self.set_viewport(self.viewport().translate(offset));
        inner(self);
        self.set_viewport(original);
    }
}

// ==========================================================================
// struct DirectRenderer
// ==========================================================================

/// A simple implementation of a Renderer that draws directly onto the CanvasEx
pub struct DirectRenderer<'a, 'alloc, C>
where
    C: Canvas,
{
    /// Target canvas
    canvas: &'a mut C,
    /// Drawing cache (decompression context, scratch-pad memory)
    cache: &'a DrawingCache<'alloc>,
}

impl<'a, 'alloc, C> DirectRenderer<'a, 'alloc, C>
where
    C: Canvas,
{
    /// Creates a new DirectRenderer instance with the given canvas
    pub fn new(
        canvas: &'a mut C,
        bg_color: Option<Color>,
        cache: &'a DrawingCache<'alloc>,
    ) -> Self {
        if let Some(color) = bg_color {
            canvas.fill_background(color);
        }

        // TODO: consider storing original canvas.viewport
        //       and restoring it by drop() function

        Self { canvas, cache }
    }
}

impl<'a, 'alloc, C> Renderer<'alloc> for DirectRenderer<'a, 'alloc, C>
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
            shape.draw(self.canvas, self.cache);
            shape.cleanup(self.cache);
        }
    }
}

pub struct ScopedRenderer<'alloc, 'env, T>
where
    'env: 'alloc,
    T: Renderer<'alloc>,
{
    pub renderer: T,
    _env: core::marker::PhantomData<&'env mut &'env ()>,
    _alloc: core::marker::PhantomData<&'alloc ()>,
}

impl<'alloc, T> ScopedRenderer<'alloc, '_, T>
where
    T: Renderer<'alloc>,
{
    pub fn new(renderer: T) -> Self {
        Self {
            renderer,
            _env: core::marker::PhantomData,
            _alloc: core::marker::PhantomData,
        }
    }

    pub fn into_inner(self) -> T {
        self.renderer
    }
}

impl<'alloc, T> Renderer<'alloc> for ScopedRenderer<'alloc, '_, T>
where
    T: Renderer<'alloc>,
{
    fn viewport(&self) -> Viewport {
        self.renderer.viewport()
    }

    fn set_viewport(&mut self, viewport: Viewport) {
        self.renderer.set_viewport(viewport);
    }

    fn render_shape<S>(&mut self, shape: S)
    where
        S: Shape<'alloc> + ShapeClone<'alloc>,
    {
        self.renderer.render_shape(shape);
    }
}
