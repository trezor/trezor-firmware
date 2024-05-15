use crate::ui::{
    display::Color,
    geometry::{Offset, Point, Rect},
    shape::{Canvas, DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

use core::f32::consts::SQRT_2;

const STAR_COUNT: usize = 8;
const RADIUS: i16 = 3;
const DIAGONAL: i16 = ((RADIUS as f32 * SQRT_2) / 2_f32) as i16;

// Offset of the normal point and then the extra offset for the main point
static STARS: [(Offset, Offset); STAR_COUNT] = [
    (Offset::y(-RADIUS), Offset::y(-1)),
    (Offset::new(DIAGONAL, -DIAGONAL), Offset::new(1, -1)),
    (Offset::x(RADIUS), Offset::x(1)),
    (Offset::new(DIAGONAL, DIAGONAL), Offset::new(1, 1)),
    (Offset::y(RADIUS), Offset::y(1)),
    (Offset::new(-DIAGONAL, DIAGONAL), Offset::new(-1, 1)),
    (Offset::x(-RADIUS), Offset::x(-1)),
    (Offset::new(-DIAGONAL, -DIAGONAL), Offset::new(-1, -1)),
];

/// A shape of a TS3 small loader
pub struct LoaderSmall {
    /// Position of point (0,0)
    pos: Point,
    /// Value 0..1000
    value: u16,
    /// Color
    color: Color,
}

impl LoaderSmall {
    pub fn new(pos: Point, value: u16) -> Self {
        Self {
            pos,
            value,
            color: Color::white(),
        }
    }

    pub fn with_color(self, color: Color) -> Self {
        Self { color, ..self }
    }

    pub fn render<'s>(self, renderer: &mut impl Renderer<'s>) {
        renderer.render_shape(self);
    }
}

impl Shape<'_> for LoaderSmall {
    fn bounds(&self) -> Rect {
        Rect::from_top_left_and_size(self.pos, Offset::uniform(1)).expand(RADIUS + 1)
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache) {
        // Calculate index of the highlighted star
        let sel_idx = (STAR_COUNT * self.value as usize / 1000) % STAR_COUNT;

        for (i, (star_offset, hili_offset)) in STARS.iter().enumerate() {
            if (sel_idx + 1) % STAR_COUNT != i {
                // Draw a star if it's not behind the highlighted one (clockwise)
                let star_pos = self.pos + *star_offset;
                canvas.draw_pixel(star_pos, self.color);
                if sel_idx == i {
                    // Higlight the main star
                    canvas.draw_pixel(star_pos + *hili_offset, self.color);
                }
            }
        }
    }
}

impl<'s> ShapeClone<'s> for LoaderSmall {
    fn clone_at_bump<T>(self, bump: &'s T) -> Option<&'s mut dyn Shape>
    where
        T: LocalAllocLeakExt<'s>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(LoaderSmall { ..self }))
    }
}
