use crate::ui::{canvas::Canvas, geometry::Rect};

use super::DrawingCache;

use without_alloc::alloc::LocalAllocLeakExt;

// ==========================================================================
// trait Shape
// ==========================================================================

/// This trait is used internally by so-called Renderers -
/// `DirectRenderer` & `ProgressiveRederer`.
///
/// All shapes (like `Bar`, `Text`, `Circle`, ...) that can be rendered
/// must implement `Shape` trait.
///
/// `Shape` objects may use `DrawingCache` as a scratch-pad memory or for
/// caching expensive calculations results.
pub trait Shape<'s> {
    /// Returns the smallest bounding rectangle containing whole parts of the
    /// shape.
    ///
    /// The function is used by renderer for optimization if the shape
    /// must be renderer or not.
    fn bounds(&self, cache: &DrawingCache<'s>) -> Rect;

    /// Draws shape on the canvas.
    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'s>);

    /// The function should release all allocated resources needed
    /// for shape drawing.
    ///
    /// It's called by renderer if the shape's draw() function won't be called
    /// anymore.
    fn cleanup(&mut self, cache: &DrawingCache<'s>);
}

// ==========================================================================
// trait ShapeClone
// ==========================================================================

/// All shapes (like `Bar`, `Text`, `Circle`, ...) that can be rendered
/// by `ProgressiveRender` must implement `ShapeClone`.
pub trait ShapeClone<'s> {
    /// Clones a shape object at the specified memory bump.
    ///
    /// The method is used by `ProgressiveRenderer` to store shape objects for
    /// deferred drawing.
    fn clone_at_bump<'alloc, T>(self, bump: &'alloc T) -> Option<&'alloc mut dyn Shape<'s>>
    where
        T: LocalAllocLeakExt<'alloc>,
        'alloc: 's;
}
