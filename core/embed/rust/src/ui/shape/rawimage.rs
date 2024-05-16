use crate::ui::geometry::Rect;

use super::{BitmapView, Canvas, DrawingCache, Renderer, Shape, ShapeClone};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for rendering compressed TOIF images.
pub struct RawImage<'a> {
    /// Destination area
    area: Rect,
    // Bitmap reference
    bitmap: BitmapView<'a>,
}

impl<'a> RawImage<'a> {
    pub fn new(area: Rect, bitmap: BitmapView<'a>) -> Self {
        Self { area, bitmap }
    }

    pub fn render(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }
}

impl<'a> Shape<'a> for RawImage<'a> {
    fn bounds(&self) -> Rect {
        self.area
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache<'a>) {
        canvas.draw_bitmap(self.area, self.bitmap);
    }
}

impl<'a> ShapeClone<'a> for RawImage<'a> {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(RawImage { ..self }))
    }
}
