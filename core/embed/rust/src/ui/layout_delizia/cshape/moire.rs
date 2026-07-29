use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
    shape::{Bitmap, BitmapFormat, Canvas, DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

use super::proto_util::visible_abs;

/// Line pitch of the two gratings, in pixels. They differ by one pixel, which
/// is what produces the travelling beat: the interference repeats every
/// `PITCH_A * PITCH_B` pixels.
const PITCH_A: i32 = 7;
const PITCH_B: i32 = 8;
/// Grating scroll rate, pixels per second, applied in opposite directions.
const SCROLL: f32 = 11.0;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum MoireDir {
    /// Lines run across the screen; the pattern is constant along x.
    Horizontal,
    /// Lines run down the screen; the pattern is constant along y.
    Vertical,
    /// Lines run at 45 degrees.
    Diagonal,
}

/// Two superimposed line gratings scrolling against each other.
///
/// The real thing would be two overlaid images; generating both procedurally is
/// far cheaper here (no decode, no buffers) and lets the pitches and scroll
/// rates be animated freely.
pub struct Moire {
    area: Rect,
    dir: MoireDir,
    secs: f32,
    fg: Color,
    bg: Color,
}

impl Moire {
    pub fn new(area: Rect, dir: MoireDir, secs: f32, fg: Color, bg: Color) -> Self {
        Self {
            area,
            dir,
            secs,
            fg,
            bg,
        }
    }

    pub fn render<'a>(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }

    /// Coordinate the gratings are a function of, for the given pixel.
    fn coord(&self, x: i16, y: i16) -> i32 {
        match self.dir {
            MoireDir::Horizontal => y as i32,
            MoireDir::Vertical => x as i32,
            MoireDir::Diagonal => x as i32 + y as i32,
        }
    }

    /// True where the two gratings disagree — the interference fringes.
    fn lit(&self, coord: i32) -> bool {
        let shift = (self.secs * SCROLL) as i32;
        let a = (coord + shift).rem_euclid(PITCH_A) < PITCH_A / 2;
        let b = (coord - shift).rem_euclid(PITCH_B) < PITCH_B / 2;
        a != b
    }

    fn color(&self, x: i16, y: i16) -> Color {
        if self.lit(self.coord(x, y)) {
            self.fg
        } else {
            self.bg
        }
    }

    /// Horizontal gratings are constant along x, so a whole row is one fill.
    /// The other two vary per pixel and need a rasterised row.
    fn varies_along_x(&self) -> bool {
        !matches!(self.dir, MoireDir::Horizontal)
    }
}

impl<'a> Shape<'a> for Moire {
    fn bounds(&self) -> Rect {
        self.area
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        let visible = visible_abs(&*canvas, self.bounds());
        if visible.is_empty() {
            return;
        }

        if !self.varies_along_x() {
            // One full-width fill per row.
            for y in visible.y0..visible.y1 {
                let rect = Rect {
                    x0: visible.x0,
                    y0: y,
                    x1: visible.x1,
                    y1: y + 1,
                };
                canvas.fill_rect(rect, self.color(visible.x0, y), 255);
            }
            return;
        }

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

        // Vertical gratings do not depend on y, so one row serves the whole
        // slice. Diagonal ones shift by one pixel per row and must be rebuilt.
        let rebuild_each_row = matches!(self.dir, MoireDir::Diagonal);
        let mut built = false;

        for y in visible.y0..visible.y1 {
            if rebuild_each_row || !built {
                let px = unwrap!(row.row_mut::<u16>(0), "No row");
                for (idx, x) in (visible.x0..visible.x1).enumerate() {
                    px[idx] = self.color(x, y).to_u16();
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
    }
}

impl<'a> ShapeClone<'a> for Moire {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(Moire { ..self }))
    }
}
