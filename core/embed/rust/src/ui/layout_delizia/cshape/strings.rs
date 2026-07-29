use crate::ui::{
    display::Color,
    geometry::Rect,
    lerp::Lerp,
    shape::{Canvas, DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

use super::proto_util::{fract, sin_turns, visible_abs};

/// Number of strings.
const COUNT: u32 = 6;
/// Line thickness, in pixels.
const THICK: i16 = 2;
/// Peak displacement at `pulse == 1.0`, in pixels.
const MAX_AMP: f32 = 15.0;

/// Horizontal lines vibrating like plucked strings.
///
/// Each string is pinned at both ends and displaced by its fundamental mode —
/// a half sine over the span — scaled by an oscillation in time and a decaying
/// pluck envelope. Strings are re-plucked on staggered periods so the set never
/// goes fully still.
pub struct Strings {
    area: Rect,
    secs: f32,
    /// Oscillation strength multiplier; 1.0 is the nominal amplitude.
    pulse: f32,
    hot: Color,
    cold: Color,
}

impl Strings {
    pub fn new(area: Rect, secs: f32, pulse: f32, hot: Color, cold: Color) -> Self {
        Self {
            area,
            secs,
            pulse,
            hot,
            cold,
        }
    }

    pub fn render<'a>(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }

    /// (resting row, current amplitude in px, temporal frequency, envelope
    /// 0..1)
    fn string(&self, i: u32) -> (f32, f32, f32, f32) {
        let n = COUNT as f32;
        let base = self.area.y0 as f32 + (i as f32 + 1.0) * (self.area.height() as f32) / (n + 1.0);

        // Thinner strings ring faster, as on a real instrument.
        let freq = 2.0 + i as f32 * 0.9;

        // Staggered pluck periods, so plucks do not line up.
        let period = 2.2 + i as f32 * 0.37;
        let u = fract(self.secs / period + i as f32 * 0.31);
        // Quadratic decay after each pluck.
        let env = (1.0 - u) * (1.0 - u);

        let amp = MAX_AMP * self.pulse * env;
        (base, amp, freq, env)
    }

    /// Row of string `i` at absolute column `x`.
    fn row_at(&self, base: f32, amp: f32, freq: f32, x: i16) -> i16 {
        let w = self.area.width() as f32;
        let xn = if w > 0.0 {
            (x - self.area.x0) as f32 / w
        } else {
            0.0
        };

        // Fundamental mode: half a sine across the span, zero at both ends.
        let mode = sin_turns(0.5 * xn);
        let disp = amp * mode * sin_turns(freq * self.secs);
        (base + disp) as i16
    }
}

impl<'a> Shape<'a> for Strings {
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
            let (base, amp, freq, env) = self.string(i);

            // Cheap reject: a string whose whole travel range misses this slice
            // costs one comparison rather than a scan across the width.
            let lo = base - amp - THICK as f32;
            let hi = base + amp + THICK as f32;
            if hi < visible.y0 as f32 || lo > visible.y1 as f32 {
                continue;
            }

            // Brighter while ringing hard.
            let color = Color::lerp(self.cold, self.hot, env);

            // Walk the span and merge columns that land on the same row, so a
            // string costs tens of fills rather than one per column.
            let mut run_y = i16::MIN;
            let mut run_x0 = visible.x0;

            for x in visible.x0..visible.x1 {
                let y = self.row_at(base, amp, freq, x);
                if y != run_y {
                    if run_y != i16::MIN {
                        self.emit(canvas, run_x0, x, run_y, color, visible);
                    }
                    run_y = y;
                    run_x0 = x;
                }
            }
            if run_y != i16::MIN {
                self.emit(canvas, run_x0, visible.x1, run_y, color, visible);
            }
        }
    }
}

impl Strings {
    #[allow(clippy::too_many_arguments)]
    fn emit(&self, canvas: &mut dyn Canvas, x0: i16, x1: i16, y: i16, color: Color, clip: Rect) {
        let rect = Rect {
            x0: x0.max(clip.x0),
            y0: y.max(clip.y0),
            x1: x1.min(clip.x1),
            y1: (y + THICK).min(clip.y1),
        };
        if !rect.is_empty() {
            canvas.fill_rect(rect, color, 255);
        }
    }
}

impl<'a> ShapeClone<'a> for Strings {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(Strings { ..self }))
    }
}
