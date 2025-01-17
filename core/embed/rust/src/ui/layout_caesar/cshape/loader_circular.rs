use crate::ui::{
    display::Color,
    geometry::{Offset, Point, Rect},
    shape::{Canvas, DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

static CELLS: [Offset; 24] = [
    Offset::new(1, -4),
    Offset::new(2, -4),
    Offset::new(3, -3),
    Offset::new(4, -2),
    Offset::new(4, -1),
    Offset::new(4, 0),
    Offset::new(4, 1),
    Offset::new(4, 2),
    Offset::new(3, 3),
    Offset::new(2, 4),
    Offset::new(1, 4),
    Offset::new(0, 4),
    Offset::new(-1, 4),
    Offset::new(-2, 4),
    Offset::new(-3, 3),
    Offset::new(-4, 2),
    Offset::new(-4, 1),
    Offset::new(-4, 0),
    Offset::new(-4, -1),
    Offset::new(-4, -2),
    Offset::new(-3, -3),
    Offset::new(-2, -4),
    Offset::new(-1, -4),
    Offset::new(0, -4),
];

pub struct LoaderCircular {
    /// Position of point (0,0)
    pos: Point,
    /// Value 0..1000
    value: u16,
    /// Color
    color: Color,
    /// Scale (length of square size)
    scale: i16,
}

impl LoaderCircular {
    pub fn new(pos: Point, value: u16) -> Self {
        Self {
            pos,
            value,
            color: Color::white(),
            scale: 2,
        }
    }

    pub fn with_color(self, color: Color) -> Self {
        Self { color, ..self }
    }

    pub fn with_scale(self, scale: i16) -> Self {
        Self { scale, ..self }
    }

    fn cells(&self) -> &[Offset] {
        let value = self.value.clamp(0, 1000);
        let last = (CELLS.len() * value as usize) / 1000;
        &CELLS[..last]
    }

    fn cell_rect(&self, offset: Offset) -> Rect {
        let pt = Point::new(
            self.pos.x + (offset.x * self.scale) - self.scale / 2,
            self.pos.y + (offset.y * self.scale) - self.scale / 2,
        );
        Rect::from_top_left_and_size(pt, Offset::uniform(self.scale))
    }

    pub fn render<'s>(self, renderer: &mut impl Renderer<'s>) {
        renderer.render_shape(self);
    }
}

impl<'s> Shape<'s> for LoaderCircular {
    fn bounds(&self) -> Rect {
        let cells = self.cells();

        if cells.is_empty() {
            Rect::zero()
        } else {
            let mut b = self.cell_rect(cells[0]);
            cells[1..]
                .iter()
                .for_each(|c| b = b.union(self.cell_rect(*c)));
            b
        }
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache) {
        for c in self.cells().iter() {
            canvas.fill_rect(self.cell_rect(*c), self.color, 255);
        }
    }
}

impl<'s> ShapeClone<'s> for LoaderCircular {
    fn clone_at_bump<T>(self, bump: &'s T) -> Option<&'s mut dyn Shape>
    where
        T: LocalAllocLeakExt<'s>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(LoaderCircular { ..self }))
    }
}
