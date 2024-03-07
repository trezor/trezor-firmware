use crate::ui::{
    canvas::{BasicCanvas, Canvas, Rgb565Canvas, Viewport},
    display::Color,
    geometry::{Offset, Point, Rect},
    shape::{DrawingCache, Shape, ShapeClone},
};

use without_alloc::{alloc::LocalAllocLeakExt, FixedVec};

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
        if self.canvas.viewport().contains(shape.bounds(self.cache)) {
            shape.draw(self.canvas, self.cache);
            shape.cleanup(self.cache);
        }
    }
}

// ==========================================================================
// struct ProgressiveRenderer
// ==========================================================================

struct ShapeHolder<'a> {
    shape: &'a mut dyn Shape<'a>,
    viewport: Viewport,
}

/// A more advanced Renderer implementation that supports deferred rendering.
pub struct ProgressiveRenderer<'a, 'alloc, T, C>
where
    T: LocalAllocLeakExt<'alloc>,
    C: BasicCanvas,
{
    /// Target canvas
    canvas: &'a mut C,
    /// Bump for cloning shapes
    bump: &'alloc T,
    /// List of rendered shapes
    shapes: FixedVec<'alloc, ShapeHolder<'alloc>>,
    /// Current viewport
    viewport: Viewport,
    // Default background color
    bg_color: Option<Color>,
    /// Drawing cache (decompression context, scratch-pad memory)
    cache: &'a DrawingCache<'alloc>,
}

impl<'a, 'alloc, T, C> ProgressiveRenderer<'a, 'alloc, T, C>
where
    T: LocalAllocLeakExt<'alloc>,
    C: BasicCanvas,
{
    /// Creates a new ProgressiveRenderer instance
    pub fn new(
        canvas: &'a mut C,
        bg_color: Option<Color>,
        cache: &'a DrawingCache<'alloc>,
        bump: &'alloc T,
        max_shapes: usize,
    ) -> Self {
        let viewport = canvas.viewport();
        Self {
            canvas,
            bump,
            shapes: unwrap!(bump.fixed_vec(max_shapes), "No shape memory"),
            viewport,
            bg_color,
            cache,
        }
    }

    /// Renders stored shapes onto the specified canvas
    pub fn render(&mut self, lines: usize) {
        let canvas_clip = self.canvas.viewport().clip;
        let canvas_origin = self.canvas.viewport().origin;

        let buff = &mut unwrap!(self.cache.render_buff(), "No render buffer");

        let mut slice = unwrap!(
            Rgb565Canvas::new(
                Offset::new(canvas_clip.width(), lines as i16),
                Some(1),
                &mut buff[..],
            ),
            "No render memory"
        );

        for y in (canvas_clip.y0..canvas_clip.y1).step_by(lines) {
            // Calculate the coordinates of the slice we will draw into
            let slice_r = Rect::new(
                // slice_r is in absolute coordinates
                Point::new(canvas_clip.x0, y),
                Point::new(canvas_clip.x1, y + lines as i16),
            )
            .translate(-canvas_origin);

            // Clear the slice background
            if let Some(color) = self.bg_color {
                slice.set_viewport(Viewport::from_size(slice_r.size()));
                slice.fill_background(color);
            }

            // Draw all shapes that overlaps the slice
            for holder in self.shapes.iter_mut() {
                let shape_viewport = holder.viewport.absolute_clip(slice_r);
                let shape_bounds = holder.shape.bounds(self.cache);

                // Is the shape overlapping the current slice?
                if shape_viewport.contains(shape_bounds) {
                    slice.set_viewport(shape_viewport.translate((-slice_r.top_left()).into()));
                    holder.shape.draw(&mut slice, self.cache);

                    if shape_bounds.y1 + shape_viewport.origin.y <= shape_viewport.clip.y1 {
                        // The shape will never be drawn again
                        holder.shape.cleanup(self.cache);
                    }
                }
            }
            self.canvas.draw_bitmap(slice_r, slice.view());
        }
    }
}

impl<'a, 'alloc, T, C> Renderer<'alloc> for ProgressiveRenderer<'a, 'alloc, T, C>
where
    T: LocalAllocLeakExt<'alloc>,
    C: BasicCanvas,
{
    fn viewport(&self) -> Viewport {
        self.viewport
    }

    fn set_viewport(&mut self, viewport: Viewport) {
        self.viewport = viewport.absolute_clip(self.canvas.bounds());
    }

    fn render_shape<S>(&mut self, shape: S)
    where
        S: Shape<'alloc> + ShapeClone<'alloc>,
    {
        // Is the shape visible?
        if self.viewport.contains(shape.bounds(self.cache)) {
            // Clone the shape & push it to the list
            let holder = ShapeHolder {
                shape: unwrap!(shape.clone_at_bump(self.bump), "No shape memory"),
                viewport: self.viewport,
            };
            unwrap!(self.shapes.push(holder), "Shape list full");
        }
    }
}
