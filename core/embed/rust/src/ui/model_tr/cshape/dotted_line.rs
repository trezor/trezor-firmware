use crate::ui::{
    canvas::Canvas,
    display::Color,
    geometry::{Offset, Point, Rect},
    shape::{DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

// Shape of horizontal solid/dotted line
pub struct HorizontalLine {
    /// Position of the left-top point
    pos: Point,
    // Length of the line
    length: i16,
    /// Line thickness (default 1)
    thickness: u8,
    /// Steps of dots (default 0 - full line)
    step: u8,
    /// Color
    color: Color,
}

impl HorizontalLine {
    pub fn new(pos: Point, length: i16) -> Self {
        Self {
            pos,
            length,
            thickness: 1,
            step: 0,
            color: Color::white(),
        }
    }

    pub fn with_color(self, color: Color) -> Self {
        Self { color, ..self }
    }

    pub fn with_thickness(self, thickness: u8) -> Self {
        Self { thickness, ..self }
    }

    pub fn with_step(self, step: u8) -> Self {
        Self { step, ..self }
    }

    pub fn render<'s>(self, renderer: &mut impl Renderer<'s>) {
        renderer.render_shape(self);
    }
}

impl<'s> Shape<'s> for HorizontalLine {
    fn bounds(&self, _cache: &DrawingCache<'s>) -> Rect {
        let size = Offset::new(self.length, self.thickness as i16);
        Rect::from_top_left_and_size(self.pos, size)
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache) {
        if self.step <= self.thickness {
            // Solid line
            let size = Offset::new(self.length, self.thickness as i16);
            let r = Rect::from_top_left_and_size(self.pos, size);
            canvas.fill_rect(r, self.color);
        } else {
            // Dotted line
            let thickness = self.thickness as i16;
            for x in (0..self.length - thickness).step_by(self.step as usize) {
                let r = Rect::from_top_left_and_size(
                    self.pos + Offset::x(x),
                    Offset::uniform(thickness),
                );
                canvas.fill_rect(r, self.color);
            }
        }
    }
}

impl<'s> ShapeClone<'s> for HorizontalLine {
    fn clone_at_bump<'alloc, T>(self, bump: &'alloc T) -> Option<&'alloc mut dyn Shape<'s>>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let clone = bump.alloc_t::<HorizontalLine>()?;
        Some(clone.uninit.init(HorizontalLine { ..self }))
    }
}
