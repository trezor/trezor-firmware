use crate::ui::{
    display::Color,
    geometry::{Point, Rect},
    lerp::Lerp,
    shape::{Canvas, DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

use super::proto_util::{cos_turns, saturate, sin_turns, visible_abs};

/// Lattice pitch. Equal to the slice height so that a dot, whose radius is
/// capped at `MAX_R < CELL / 2`, always falls entirely inside a single slice —
/// it is therefore drawn exactly once per frame rather than once per slice it
/// straddles.
const CELL: i16 = 16;
/// Largest dot radius. Must stay below `CELL / 2`.
const MAX_R: i16 = 7;

/// Halftone: a lattice of dots whose radii track a drifting interference field.
pub struct Halftone {
    area: Rect,
    secs: f32,
    dot: Color,
    dim: Color,
}

impl Halftone {
    pub fn new(area: Rect, secs: f32, dot: Color, dim: Color) -> Self {
        Self {
            area,
            secs,
            dot,
            dim,
        }
    }

    pub fn render<'a>(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }

    /// Field value in 0..1 at lattice cell (i, j).
    ///
    /// Three superimposed waves rather than a radial ripple, which avoids
    /// needing a square root — `f32::sqrt` is std-only here.
    fn intensity(&self, i: i16, j: i16) -> f32 {
        let fx = i as f32 * 0.11;
        let fy = j as f32 * 0.11;
        let t = self.secs;

        let a = sin_turns(fx + t * 0.13);
        let b = cos_turns(fy - t * 0.09);
        let c = sin_turns((fx + fy) * 0.6 + t * 0.05);

        saturate(0.5 + 0.5 * (a + b + c) / 3.0)
    }
}

impl<'a> Shape<'a> for Halftone {
    fn bounds(&self) -> Rect {
        self.area
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache<'a>) {
        let bounds = self.bounds();
        let visible = visible_abs(&*canvas, bounds);
        if visible.is_empty() {
            return;
        }

        let half = CELL / 2;

        // Only the lattice rows whose dot centres fall in this slice.
        let first_j = (visible.y0 - bounds.y0) / CELL;
        let last_j = (visible.y1 - 1 - bounds.y0) / CELL;
        let first_i = (visible.x0 - bounds.x0) / CELL;
        let last_i = (visible.x1 - 1 - bounds.x0) / CELL;

        for j in first_j..=last_j {
            let cy = bounds.y0 + j * CELL + half;
            if cy < visible.y0 || cy >= visible.y1 {
                continue;
            }
            for i in first_i..=last_i {
                let cx = bounds.x0 + i * CELL + half;

                let v = self.intensity(i, j);
                let radius = 1 + (v * (MAX_R - 1) as f32) as i16;

                let color = Color::lerp(self.dim, self.dot, v);
                canvas.fill_circle(Point::new(cx, cy), radius, color, 255);
            }
        }
    }
}

impl<'a> ShapeClone<'a> for Halftone {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(Halftone { ..self }))
    }
}
