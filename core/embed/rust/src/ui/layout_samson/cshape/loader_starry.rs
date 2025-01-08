use crate::ui::{
    display::Color,
    geometry::{Offset, Point, Rect},
    shape::{Canvas, DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

use core::f32::consts::SQRT_2;

const STAR_COUNT: usize = 8;
const STAR_SMALL: i16 = 2;
const STAR_MEDIUM: i16 = 4;
const STAR_LARGE: i16 = 6;

const RADIUS: i16 = 13;
const DIAGONAL: i16 = ((RADIUS as f32 * SQRT_2) / 2_f32) as i16;

// Offset of the normal point and then the extra offset for the main point
static STARS: [Offset; STAR_COUNT] = [
    Offset::y(-RADIUS),
    Offset::new(DIAGONAL, -DIAGONAL),
    Offset::x(RADIUS),
    Offset::new(DIAGONAL, DIAGONAL),
    Offset::y(RADIUS),
    Offset::new(-DIAGONAL, DIAGONAL),
    Offset::x(-RADIUS),
    Offset::new(-DIAGONAL, -DIAGONAL),
];

/// A shape of a TS3 starry loader
pub struct LoaderStarry {
    /// Position of point (0,0)
    pos: Point,
    /// Value 0..1000
    value: u16,
    /// Color
    color: Color,
}

impl LoaderStarry {
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

    fn draw_large_star(&self, canvas: &mut dyn Canvas, offset: Offset) {
        let r = Rect::from_center_and_size(self.pos + offset, Offset::uniform(STAR_LARGE));
        canvas.fill_round_rect(r, 2, self.color, 255);
    }

    fn draw_medium_star(&self, canvas: &mut dyn Canvas, offset: Offset) {
        let r = Rect::from_center_and_size(self.pos + offset, Offset::uniform(STAR_MEDIUM));
        canvas.fill_round_rect(r, 1, self.color, 255);
    }

    fn draw_small_star(&self, canvas: &mut dyn Canvas, offset: Offset) {
        let r = Rect::from_center_and_size(self.pos + offset, Offset::uniform(STAR_SMALL));
        canvas.fill_rect(r, self.color, 255);
    }
}

impl Shape<'_> for LoaderStarry {
    fn bounds(&self) -> Rect {
        Rect::from_top_left_and_size(self.pos, Offset::uniform(1)).expand(RADIUS + STAR_LARGE)
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache) {
        // Calculate the index of the big star
        let sel_idx = (STAR_COUNT * self.value as usize / 1000) % STAR_COUNT;

        for (i, c) in STARS.iter().enumerate() {
            if i == sel_idx {
                self.draw_large_star(canvas, *c);
            } else if (sel_idx + 1) % 8 == i || (sel_idx - 1) % 8 == i {
                self.draw_medium_star(canvas, *c);
            } else {
                self.draw_small_star(canvas, *c);
            }
        }
    }
}

impl<'s> ShapeClone<'s> for LoaderStarry {
    fn clone_at_bump<T>(self, bump: &'s T) -> Option<&'s mut dyn Shape>
    where
        T: LocalAllocLeakExt<'s>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(LoaderStarry { ..self }))
    }
}
