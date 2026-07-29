use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
    lerp::Lerp,
    shape::{Bitmap, BitmapFormat, Canvas, DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

use super::proto_util::{fract, hash_u32, visible_abs};

/// Half width of the bulbs, in pixels.
const HALF_W: f32 = 52.0;
/// Half width at the neck.
const NECK_W: f32 = 3.0;
/// Thickness of the glass wall and the end plates.
const FRAME: i16 = 2;
/// Half width of the falling stream.
const STREAM_HALF: i16 = 2;
/// Seconds for one full pour.
const PERIOD_S: f32 = 5.0;
/// How far the upper surface dips at the centre as it drains, in pixels.
const FUNNEL_DEPTH: f32 = 15.0;
/// Rise of the lower pile per pixel away from its centre.
const MOUND_SLOPE: f32 = 0.42;
/// Grain shades, as blend factors from the sand colour toward the glass colour.
const GRAIN: [f32; 4] = [0.0, 0.13, 0.28, 0.44];

/// An hourglass pouring sand.
///
/// Rendered per pixel into a scratch row rather than as flat spans: the sand is
/// a stipple of four shades, the upper surface funnels as it drains and the
/// lower sand builds into a cone. A solid fill reads as a moving bar rather
/// than as sand.
pub struct SandClock {
    area: Rect,
    secs: f32,
    glass: Color,
    frame: Color,
    sand: Color,
}

impl SandClock {
    pub fn new(area: Rect, secs: f32, glass: Color, frame: Color, sand: Color) -> Self {
        Self {
            area,
            secs,
            glass,
            frame,
            sand,
        }
    }

    pub fn render<'a>(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }

    /// Half width of the glass at absolute row `y`.
    fn half_width(&self, y: i16) -> f32 {
        let top = self.area.y0 as f32;
        let bottom = self.area.y1 as f32;
        let neck = (top + bottom) * 0.5;

        if (y as f32) < neck {
            let k = ((y as f32) - top) / (neck - top);
            HALF_W + (NECK_W - HALF_W) * k
        } else {
            let k = ((y as f32) - neck) / (bottom - neck);
            NECK_W + (HALF_W - NECK_W) * k
        }
    }

    /// Pour progress, 0 = upper bulb full, 1 = lower bulb full.
    fn progress(&self) -> f32 {
        fract(self.secs / PERIOD_S)
    }

    /// One of four sand shades, picked by a hash of the position.
    ///
    /// `drift` shifts the sampling lattice so the falling stream appears to
    /// move, while settled sand keeps a fixed texture.
    fn grain(&self, x: i16, y: i16, drift: i32) -> Color {
        let key = ((x as i32) << 16) ^ (y as i32 + drift);
        let h = hash_u32(key as u32);
        let shade = GRAIN[((h >> 7) & 3) as usize];
        Color::lerp(self.sand, self.glass, shade)
    }

    fn pixel(&self, x: i16, y: i16, cx: i16) -> Color {
        let top = self.area.y0;
        let bottom = self.area.y1;
        let neck = (top + bottom) / 2;

        let adx = (x - cx).abs() as f32;
        let hw = self.half_width(y);

        // Outside the silhouette.
        if adx >= hw {
            return Color::black();
        }

        // End plates.
        if y < top + FRAME || y >= bottom - FRAME {
            return self.frame;
        }

        // Glass walls.
        if adx >= hw - FRAME as f32 {
            return self.frame;
        }

        let p = self.progress();

        if y < neck {
            // Upper bulb: the surface sinks and funnels toward the centre.
            let level = top as f32 + (neck - top) as f32 * p;
            let dip = FUNNEL_DEPTH * (1.0 - adx / if hw > 1.0 { hw } else { 1.0 });
            if (y as f32) >= level + dip {
                return self.grain(x, y, 0);
            }
            self.glass
        } else {
            // Lower bulb: sand piles into a cone under the neck.
            let apex = bottom as f32 - (bottom - neck) as f32 * p;
            let surface = apex + MOUND_SLOPE * adx;
            if (y as f32) >= surface {
                return self.grain(x, y, 0);
            }

            // Falling stream: sparse so it reads as grains, and the lattice
            // drifts downward over time so they appear to fall.
            if adx <= STREAM_HALF as f32 {
                let drift = (self.secs * 70.0) as i32;
                let h = hash_u32((((x as i32) << 16) ^ (y as i32 + drift)) as u32);
                if h & 1 == 0 {
                    return self.grain(x, y, drift);
                }
            }
            self.glass
        }
    }
}

impl<'a> Shape<'a> for SandClock {
    fn bounds(&self) -> Rect {
        self.area
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        let bounds = self.bounds();
        let visible = visible_abs(&*canvas, bounds);
        if visible.is_empty() {
            return;
        }

        let cx = (bounds.x0 + bounds.x1) / 2;

        let buff = &mut unwrap!(cache.image_buff(), "No image buffer");
        let mut row = unwrap!(
            Bitmap::new_mut(
                BitmapFormat::RGB565,
                None,
                Offset::new(visible.width(), 1),
                None,
                &mut buff[..],
            ),
            "Too small buffer"
        );

        for y in visible.y0..visible.y1 {
            {
                let px = unwrap!(row.row_mut::<u16>(0), "No row");
                for (idx, x) in (visible.x0..visible.x1).enumerate() {
                    px[idx] = self.pixel(x, y, cx).to_u16();
                }
            }
            canvas.draw_bitmap(
                Rect {
                    x0: visible.x0,
                    y0: y,
                    x1: visible.x1,
                    y1: y + 1,
                },
                row.view(),
            );
        }
    }
}

impl<'a> ShapeClone<'a> for SandClock {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(SandClock { ..self }))
    }
}
