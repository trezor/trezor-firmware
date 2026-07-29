use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
    shape::{Bitmap, BitmapFormat, Canvas, DrawingCache, Renderer, Shape, ShapeClone},
};

use without_alloc::alloc::LocalAllocLeakExt;

use super::proto_util::{cos_turns, sin_turns, visible_abs};

/// Edge length of each square.
const SIZE: i16 = 78;
/// Hatch line pitch, in pixels.
const PITCH: i32 = 6;
/// Travel amplitude as a fraction of the free space, per axis.
const TRAVEL: f32 = 0.5;

/// Two diagonally hatched squares drifting around the screen on Lissajous
/// paths. The hatches run in opposite diagonals, so where the squares overlap
/// the two gratings interfere into a plaid.
pub struct HatchSquares {
    area: Rect,
    secs: f32,
    a: Color,
    b: Color,
    both: Color,
    bg: Color,
    /// Leave the unhatched pixels untouched so whatever was drawn underneath
    /// shows through. Costs the per-square colours: a mask blend carries one
    /// foreground colour, so the whole hatch is drawn in `a`.
    transparent: bool,
}

impl HatchSquares {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        area: Rect,
        secs: f32,
        a: Color,
        b: Color,
        both: Color,
        bg: Color,
        transparent: bool,
    ) -> Self {
        Self {
            area,
            secs,
            a,
            b,
            both,
            bg,
            transparent,
        }
    }

    pub fn render<'a>(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }

    /// The two square rectangles at the current time.
    fn squares(&self) -> (Rect, Rect) {
        let free_x = (self.area.width() - SIZE) as f32 * 0.5 * TRAVEL;
        let free_y = (self.area.height() - SIZE) as f32 * 0.5 * TRAVEL;
        let cx = (self.area.x0 + self.area.x1) as f32 * 0.5;
        let cy = (self.area.y0 + self.area.y1) as f32 * 0.5;
        let t = self.secs;

        let mk = |ox: f32, oy: f32| {
            let x0 = (cx + ox - SIZE as f32 * 0.5) as i16;
            let y0 = (cy + oy - SIZE as f32 * 0.5) as i16;
            Rect {
                x0,
                y0,
                x1: x0 + SIZE,
                y1: y0 + SIZE,
            }
        };

        // Incommensurate rates so the pair never settles into a short loop.
        let sa = mk(free_x * sin_turns(t * 0.061), free_y * cos_turns(t * 0.083));
        let sb = mk(free_x * cos_turns(t * 0.047), free_y * sin_turns(t * 0.071));
        (sa, sb)
    }

    /// Colour of the hatch at this pixel, or `None` where nothing is drawn.
    fn hatch_at(&self, x: i16, y: i16, sa: Rect, sb: Rect) -> Option<Color> {
        let p = crate::ui::geometry::Point::new(x, y);
        let in_a = sa.contains(p);
        let in_b = sb.contains(p);

        if !in_a && !in_b {
            return None;
        }

        // Opposite diagonals: "/" for A, "\" for B.
        let ha = (x as i32 + y as i32).rem_euclid(PITCH) < PITCH / 2;
        let hb = (x as i32 - y as i32).rem_euclid(PITCH) < PITCH / 2;

        match (in_a, in_b) {
            // Overlap: the two gratings interfere into a plaid.
            (true, true) => (ha != hb).then_some(self.both),
            (true, false) => ha.then_some(self.a),
            (false, true) => hb.then_some(self.b),
            (false, false) => None,
        }
    }
}

impl<'a> Shape<'a> for HatchSquares {
    fn bounds(&self) -> Rect {
        // Union of the two squares rather than the whole screen, so slices the
        // squares do not reach are skipped entirely.
        let (sa, sb) = self.squares();
        Rect {
            x0: sa.x0.min(sb.x0).max(self.area.x0),
            y0: sa.y0.min(sb.y0).max(self.area.y0),
            x1: sa.x1.max(sb.x1).min(self.area.x1),
            y1: sa.y1.max(sb.y1).min(self.area.y1),
        }
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        let visible = visible_abs(&*canvas, self.bounds());
        if visible.is_empty() {
            return;
        }

        let (sa, sb) = self.squares();

        let buff = &mut unwrap!(cache.image_buff(), "No image buffer");

        // Transparent mode builds an 8-bit coverage mask and blends it, leaving
        // untouched pixels alone. Opaque mode writes RGB565 directly and keeps
        // the per-square colours. Both are one blit per row; the diagonal hatch
        // shifts by a pixel each row, so no row can be reused.
        let format = if self.transparent {
            BitmapFormat::MONO8
        } else {
            BitmapFormat::RGB565
        };
        let mut row = unwrap!(
            Bitmap::new_mut(
                format,
                None,
                Offset::new(visible.width(), 1),
                None,
                &mut buff[..],
            ),
            "Too small buffer"
        );

        for y in visible.y0..visible.y1 {
            let dst = Rect {
                x0: visible.x0,
                y0: y,
                x1: visible.x1,
                y1: y + 1,
            };

            if self.transparent {
                {
                    let px = unwrap!(row.row_mut::<u8>(0), "No row");
                    for (idx, x) in (visible.x0..visible.x1).enumerate() {
                        px[idx] = if self.hatch_at(x, y, sa, sb).is_some() {
                            255
                        } else {
                            0
                        };
                    }
                }
                canvas.blend_bitmap(dst, row.view().with_fg(self.a));
            } else {
                {
                    let px = unwrap!(row.row_mut::<u16>(0), "No row");
                    for (idx, x) in (visible.x0..visible.x1).enumerate() {
                        px[idx] = self.hatch_at(x, y, sa, sb).unwrap_or(self.bg).to_u16();
                    }
                }
                canvas.draw_bitmap(dst, row.view());
            }
        }
    }
}

impl<'a> ShapeClone<'a> for HatchSquares {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(HatchSquares { ..self }))
    }
}
