use crate::ui::geometry::Rect;

use super::{Canvas, DrawingCache, Renderer, Shape, ShapeClone};

use without_alloc::alloc::LocalAllocLeakExt;

pub struct Blurring {
    // Blurred area
    area: Rect,
    /// Blurring kernel radius
    radius: usize,
}

/// A shape for the blurring of a specified rectangle area.
impl Blurring {
    pub fn new(area: Rect, radius: usize) -> Self {
        Self { area, radius }
    }

    pub fn render<'s>(self, renderer: &mut impl Renderer<'s>) {
        renderer.render_shape(self);
    }
}

impl Shape<'_> for Blurring {
    fn bounds(&self, _cache: &DrawingCache) -> Rect {
        self.area
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache) {
        canvas.blur_rect(self.area, self.radius, cache);
    }
}

impl<'s> ShapeClone<'s> for Blurring {
    fn clone_at_bump<'alloc, T>(self, bump: &'alloc T) -> Option<&'alloc mut dyn Shape<'s>>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let clone = bump.alloc_t::<Blurring>()?;
        Some(clone.uninit.init(Blurring { ..self }))
    }
}
