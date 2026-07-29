use crate::ui::{
    display::Color,
    geometry::Rect,
    lerp::Lerp,
    shape::{Canvas, DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

use super::proto_util::{fract, hash_f, noise1, saturate, visible_abs};

/// Number of particles. Well inside the shape budget because the whole field is
/// a *single* shape — one shape per particle would blow `SHAPE_MAX_COUNT` (45)
/// and panic.
const COUNT: u32 = 56;

/// Peak drift away from a particle's home position, in pixels.
const DRIFT: f32 = 26.0;
/// How fast the noise field evolves, in noise units per second.
const FLOW_SPEED: f32 = 0.35;
/// Upward current, pixels per second.
const RISE: f32 = 9.0;

/// Particles drifting on a smooth noise field.
///
/// Positions are a **pure function of elapsed time**, not an integration of
/// velocity. Frames here are unevenly spaced (the animation timer is "as soon
/// as possible", dispatched through the MicroPython scheduler), so integrating
/// would jitter and would need mutable state that `draw()` must not touch —
/// `draw()` is called once per slice, so any accumulation there would run 15
/// times a frame. The trade is that this is advection-flavoured wandering
/// rather than true fluid advection.
pub struct Particles {
    area: Rect,
    secs: f32,
    near: Color,
    far: Color,
}

impl Particles {
    pub fn new(area: Rect, secs: f32, near: Color, far: Color) -> Self {
        Self {
            area,
            secs,
            near,
            far,
        }
    }

    pub fn render<'a>(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }

    /// Position, size and depth of particle `i` at the current time.
    fn particle(&self, i: u32) -> (i16, i16, i16, f32) {
        let w = self.area.width() as f32;
        let h = self.area.height() as f32;

        // Home position and per-particle phase, fixed for the life of the run.
        let hx = hash_f(i * 3 + 1);
        let hy = hash_f(i * 3 + 2);
        let depth = hash_f(i * 3 + 3); // 0 = far, 1 = near

        // Nearer particles drift further and rise faster — cheap parallax.
        let scale = 0.4 + 0.6 * depth;
        let t = self.secs * FLOW_SPEED;

        let nx = noise1(i.wrapping_mul(0x9e37_79b9), t + 4.0) - 0.5;
        let ny = noise1(i.wrapping_mul(0x85eb_ca6b), t + 8.0) - 0.5;

        let x = hx * w + nx * 2.0 * DRIFT * scale;

        // Rise continuously, wrapping so the field never empties. `fract`
        // handles the negative values `rise` produces; a plain `as i32` cast
        // truncates toward zero and would not wrap upward travel correctly.
        let rise = self.secs * RISE * scale;
        let y = hy * h - rise + ny * 2.0 * DRIFT * scale;
        let span = h + 2.0 * DRIFT;
        // Into [0, span), then biased so particles enter and leave off-screen.
        let y = fract(y / span) * span - DRIFT;

        let size = if depth > 0.72 {
            4
        } else if depth > 0.36 {
            3
        } else {
            2
        };

        (
            self.area.x0 + x as i16,
            self.area.y0 + y as i16,
            size,
            depth,
        )
    }
}

impl<'a> Shape<'a> for Particles {
    fn bounds(&self) -> Rect {
        self.area
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache<'a>) {
        let visible = visible_abs(&*canvas, self.bounds());
        if visible.is_empty() {
            return;
        }

        for i in 0..COUNT {
            let (px, py, size, depth) = self.particle(i);

            // Cheap reject: only particles overlapping this slice are drawn, so
            // the per-slice cost is a bounds test, not a redraw.
            if py + size <= visible.y0 || py >= visible.y1 {
                continue;
            }

            let rect = Rect {
                x0: px.max(visible.x0),
                y0: py.max(visible.y0),
                x1: (px + size).min(visible.x1),
                y1: (py + size).min(visible.y1),
            };
            if rect.is_empty() {
                continue;
            }

            // Floor the blend so the farthest particles stay above the noise
            // on a black background rather than vanishing into it.
            let color = Color::lerp(self.far, self.near, saturate(0.35 + 0.65 * depth));
            canvas.fill_rect(rect, color, 255);
        }
    }
}

impl<'a> ShapeClone<'a> for Particles {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(Particles { ..self }))
    }
}
