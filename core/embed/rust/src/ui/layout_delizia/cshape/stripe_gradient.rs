use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
    lerp::Lerp,
    shape::{Bitmap, BitmapFormat, Canvas, DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

/// Stripe width that reproduces the blocky look: equal to the
/// `ProgressiveRenderer` slice height (see
/// `shape::display::nofb_rgb565::render_on_display`, which calls `render(16)`),
/// so a row of blocks never straddles two slices.
pub const BLOCK: i16 = 16;

/// Stripe width for a smooth, per-pixel gradient.
pub const SMOOTH: i16 = 1;

/// 4x4 ordered (Bayer) dither matrix, values 0..15.
const BAYER4: [u8; 16] = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum StripeDir {
    /// Stripes run vertically: colour varies along the x axis.
    Vertical,
    /// Stripes run horizontally: colour varies along the y axis.
    Horizontal,
}

/// A screen-filling two-colour gradient drawn as stripes of `step` pixels,
/// sweeping along the stripe axis over time.
///
/// `step == BLOCK` gives the chunky 16x16 look; `step == SMOOTH` gives a
/// continuous per-pixel gradient. Optional ordered dithering breaks up the
/// RGB565 quantisation banding that a smooth ramp otherwise shows.
///
/// Slice-aware: `draw()` rasterises only what intersects the slice it was
/// handed, so cost per frame is O(area), not O(slices x area). Contrast
/// `UnlockOverlay`, which regenerates its whole bitmap on every slice.
pub struct StripeGradient {
    area: Rect,
    dir: StripeDir,
    step: i16,
    dither: bool,
    /// Gradient sweep phase, in turns. Only the fractional part matters.
    phase: f32,
    from: Color,
    to: Color,
}

impl StripeGradient {
    pub fn new(
        area: Rect,
        dir: StripeDir,
        step: i16,
        dither: bool,
        phase: f32,
        from: Color,
        to: Color,
    ) -> Self {
        Self {
            area,
            dir,
            step: if step < 1 { 1 } else { step },
            dither,
            phase,
            from,
            to,
        }
    }

    pub fn render<'a>(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }

    /// Number of stripes along the gradient axis.
    fn steps(&self) -> i16 {
        let len = match self.dir {
            StripeDir::Vertical => self.area.width(),
            StripeDir::Horizontal => self.area.height(),
        };
        // Round up so a partial trailing stripe still gets a colour.
        (len + self.step - 1) / self.step
    }

    /// Position of the gradient ramp for stripe index `i`, in 0..1.
    fn ramp(&self, i: i16, steps: i16) -> f32 {
        let n = if steps > 0 { steps as f32 } else { 1.0 };
        let raw = i as f32 / n + self.phase;

        // Fractional part. Hand-rolled because `f32::fract`/`rem_euclid` are
        // std-only; the device build is no_std and links no libm (compare the
        // hand-written `shape::utils::sin_f32`). Using them would compile for
        // the emulator on macOS and fail for the device.
        let mut f = raw - (raw as i32) as f32;
        if f < 0.0 {
            f += 1.0;
        }

        // Triangle wave, so the sweep loops seamlessly: 0 -> 1 -> 0.
        if f < 0.5 {
            2.0 * f
        } else {
            2.0 * (1.0 - f)
        }
    }

    /// One RGB565 quantisation step expressed in ramp units, i.e. how far `t`
    /// must move to change the output colour. Dithering by roughly this much
    /// is what converts a hard band edge into a stipple.
    ///
    /// RGB565 keeps 5/6/5 bits, so the channel steps are 8/4/8 in 8-bit terms.
    fn dither_amplitude(&self) -> f32 {
        let d = |a: u8, b: u8| (a as i16 - b as i16).unsigned_abs() as f32;
        let lr = d(self.from.r(), self.to.r()) / 8.0;
        let lg = d(self.from.g(), self.to.g()) / 4.0;
        let lb = d(self.from.b(), self.to.b()) / 8.0;

        // `f32::max` is std-only, so compare by hand.
        let mut levels = lr;
        if lg > levels {
            levels = lg;
        }
        if lb > levels {
            levels = lb;
        }

        if levels > 1.0 {
            1.0 / levels
        } else {
            0.0
        }
    }

    /// Colour of the pixel at absolute screen position (x, y).
    fn color_at(&self, x: i16, y: i16, steps: i16, amplitude: f32) -> Color {
        let (pos, origin) = match self.dir {
            StripeDir::Vertical => (x, self.area.x0),
            StripeDir::Horizontal => (y, self.area.y0),
        };

        let mut t = self.ramp((pos - origin) / self.step, steps);

        if self.dither {
            // Indexed by ABSOLUTE coordinates. Indexing by slice-local y would
            // restart the pattern every 16 px and read as banding.
            let cell = BAYER4[((y & 3) * 4 + (x & 3)) as usize] as f32 / 16.0;
            t += (cell - 0.5) * amplitude;
            if t < 0.0 {
                t = 0.0;
            } else if t > 1.0 {
                t = 1.0;
            }
        }

        Color::lerp(self.from, self.to, t)
    }

    /// True when colour varies from pixel to pixel along x, which rules out
    /// filling whole rows or columns with a single `fill_rect`.
    fn varies_along_x(&self) -> bool {
        self.dither || (matches!(self.dir, StripeDir::Vertical) && self.step == 1)
    }
}

impl<'a> Shape<'a> for StripeGradient {
    fn bounds(&self) -> Rect {
        self.area
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        let bounds = self.bounds();

        // Which part of us is visible in the slice we were handed, in absolute
        // screen coordinates. Same idiom as `shape::JpegImage::draw`: the canvas
        // viewport has been translated into slice-local space, so we clip
        // against it and then translate back out.
        let clip = canvas.viewport().relative_clip(bounds).clip;
        let visible = clip.translate(-canvas.viewport().origin);

        if visible.is_empty() {
            return;
        }

        let steps = self.steps();

        if self.varies_along_x() {
            // Per-pixel along x: rasterise one row into scratch memory and blit
            // it. Doing this with `fill_rect` per pixel would be 240 blit calls
            // per row instead of one.
            let amplitude = if self.dither {
                self.dither_amplitude()
            } else {
                0.0
            };

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

            // Without dithering the row content is independent of y, so it only
            // has to be built once for the whole slice.
            let rebuild_each_row = self.dither;
            let mut built = false;

            for y in visible.y0..visible.y1 {
                if rebuild_each_row || !built {
                    let px = unwrap!(row.row_mut::<u16>(0), "No row");
                    for (idx, x) in (visible.x0..visible.x1).enumerate() {
                        px[idx] = self.color_at(x, y, steps, amplitude).to_u16();
                    }
                    built = true;
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
        } else if matches!(self.dir, StripeDir::Horizontal) {
            // Colour varies with y only: one full-width fill per stripe row.
            let first = (visible.y0 - bounds.y0) / self.step;
            let last = (visible.y1 - 1 - bounds.y0) / self.step;
            for i in first..=last {
                let y0 = bounds.y0 + i * self.step;
                let rect = Rect {
                    x0: visible.x0,
                    y0: y0.max(visible.y0),
                    x1: visible.x1,
                    y1: (y0 + self.step).min(visible.y1),
                };
                canvas.fill_rect(rect, self.color_at(visible.x0, y0, steps, 0.0), 255);
            }
        } else {
            // Colour varies with x in whole stripes: one fill per stripe column,
            // spanning the full visible height of this slice.
            let first = (visible.x0 - bounds.x0) / self.step;
            let last = (visible.x1 - 1 - bounds.x0) / self.step;
            for i in first..=last {
                let x0 = bounds.x0 + i * self.step;
                let rect = Rect {
                    x0: x0.max(visible.x0),
                    y0: visible.y0,
                    x1: (x0 + self.step).min(visible.x1),
                    y1: visible.y1,
                };
                canvas.fill_rect(rect, self.color_at(x0, visible.y0, steps, 0.0), 255);
            }
        }
    }
}

impl<'a> ShapeClone<'a> for StripeGradient {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(StripeGradient { ..self }))
    }
}
