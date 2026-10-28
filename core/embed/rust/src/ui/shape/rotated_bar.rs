use without_alloc::alloc::LocalAllocLeakExt;

use super::utils::{sin_cos_f32, sqrt_f32};
use super::{Canvas, DrawingCache, Renderer, Shape, ShapeClone};
use crate::ui::display::Color;
use crate::ui::geometry::{Point, Rect};

/// Solid spans not longer than this are written pixel by pixel instead of
/// by `fill_rect()`. On T3W1 a pixel write costs ~1.2 us, while a DMA fill
/// costs ~5.8 us (including the wait the next pixel write pays) plus ~12 ns
/// per pixel.
const MAX_CPU_SPAN: i16 = 4;

/// A shape for rendering rectangles with rounded corners rotated by
/// an arbitrary angle around their center.
///
/// The shape is rendered row by row using the signed distance function
/// of a rounded box, so it works with both the direct and the progressive
/// renderer. Only edge pixels are blended individually, solid spans are
/// filled with `fill_rect()`.
pub struct RotatedBar {
    /// Rectangle position and dimension before the rotation
    area: Rect,
    /// Foreground color (default None)
    fg_color: Option<Color>,
    /// Background color (default None)
    bg_color: Option<Color>,
    /// Thickness (default 1)
    thickness: i16,
    /// Corner radius (default 0)
    radius: i16,
    /// Clockwise rotation in degrees (default 0)
    angle: f32,
    /// Alpha (default 255)
    alpha: u8,
}

impl RotatedBar {
    pub fn new(area: Rect) -> Self {
        Self {
            area,
            fg_color: None,
            bg_color: None,
            thickness: 1,
            radius: 0,
            angle: 0.0,
            alpha: 255,
        }
    }

    pub fn with_fg(self, fg_color: Color) -> Self {
        Self {
            fg_color: Some(fg_color),
            ..self
        }
    }

    pub fn with_bg(self, bg_color: Color) -> Self {
        Self {
            bg_color: Some(bg_color),
            ..self
        }
    }

    pub fn with_radius(self, radius: i16) -> Self {
        Self { radius, ..self }
    }

    pub fn with_thickness(self, thickness: i16) -> Self {
        Self { thickness, ..self }
    }

    pub fn with_angle(self, angle: f32) -> Self {
        Self { angle, ..self }
    }

    pub fn with_alpha(self, alpha: u8) -> Self {
        Self { alpha, ..self }
    }

    pub fn render<'s>(self, renderer: &mut impl Renderer<'s>) {
        renderer.render_shape(self);
    }

    fn sdf(&self) -> RoundBoxSdf {
        RoundBoxSdf::new(self.area, self.radius, self.angle)
    }

    /// Evaluates the distance function `n` times over the shape bounds,
    /// for benchmarking. Returns the sum of the distances.
    #[doc(hidden)]
    pub fn bench_dist(&self, n: u32) -> f32 {
        let sdf = self.sdf();
        let b = sdf.bounds();
        let w = b.width().max(1) as u32;
        (0..n)
            .map(|i| {
                let x = b.x0 + (i % w) as i16;
                let y = b.y0 + (i / w) as i16 % b.height().max(1);
                let (u0, v0) = sdf.row(y);
                let x = f32::from(x);
                let (d, g) = sdf.dist_grad(u0 + sdf.cos * x, v0 - sdf.sin * x);
                d + g
            })
            .sum()
    }
}

impl Shape<'_> for RotatedBar {
    fn bounds(&self) -> Rect {
        self.sdf().bounds()
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache) {
        self.draw_on(canvas);
    }
}

impl RotatedBar {
    fn draw_on(&self, canvas: &mut dyn Canvas) {
        let sdf = self.sdf();

        // Only rows and columns that are both inside the shape bounds and
        // inside the current clip (e.g. a progressive renderer slice)
        let vp = canvas.viewport();
        let visible = vp.clip.translate(-vp.origin).clamp(sdf.bounds());
        if visible.is_empty() {
            return;
        }

        let th = f32::from(self.thickness) * sdf.scale;
        let size = self.area.width().min(self.area.height());

        // Same semantics as `Bar`:
        // - fg + bg => outline in fg, inside filled with bg
        // - fg only => outline only
        // - bg only => filled shape
        // - outline too thick => filled with fg
        //
        // Each pass is (color, inset, hole)
        let passes: [Option<(Color, f32, Option<f32>)>; 2] = match (self.fg_color, self.bg_color) {
            (Some(fg), _) if self.thickness * 2 >= size => [Some((fg, 0.0, None)), None],
            (Some(fg), Some(bg)) if self.thickness > 0 => {
                [Some((fg, 0.0, None)), Some((bg, th, None))]
            }
            (Some(fg), None) if self.thickness > 0 => [Some((fg, 0.0, Some(th))), None],
            (_, Some(bg)) => [Some((bg, 0.0, None)), None],
            _ => return,
        };

        for y in visible.y0..visible.y1 {
            let (u0, v0) = sdf.row(y);
            for (color, inset, hole) in passes.iter().flatten() {
                let row = Row {
                    sdf: &sdf,
                    y,
                    u0,
                    v0,
                    x0: visible.x0,
                    x1: visible.x1,
                    color: *color,
                    alpha: self.alpha,
                };
                row.draw(canvas, *inset, *hole);
            }
        }
    }
}

impl<'s> ShapeClone<'s> for RotatedBar {
    fn clone_at_bump<T>(self, bump: &'s T) -> Option<&'s mut dyn Shape<'s>>
    where
        T: LocalAllocLeakExt<'s>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(RotatedBar { ..self }))
    }
}

/// Signed distance function of a rotated rectangle with rounded corners.
///
/// Negative inside the shape, positive outside. The distance is scaled by
/// `scale`, see below.
struct RoundBoxSdf {
    /// Center of the box
    cx: f32,
    cy: f32,
    /// sin/cos of the rotation angle
    sin: f32,
    cos: f32,
    /// Half-size of the box without the rounded corners
    bx: f32,
    by: f32,
    /// Corner radius
    radius: f32,
    /// Distance scale 1 / (|sin| + |cos|) - the width of a pixel measured
    /// across a rotated edge. With it, the linear coverage ramp sums
    /// exactly to the covered area at both 0 and 45 degrees.
    scale: f32,
}

impl RoundBoxSdf {
    fn new(area: Rect, radius: i16, angle: f32) -> Self {
        let hx = f32::from(area.width()) / 2.0;
        let hy = f32::from(area.height()) / 2.0;
        let radius = f32::from(radius.max(0)).min(hx).min(hy);
        let (sin, cos) = sin_cos_f32(angle);
        Self {
            cx: f32::from(area.x0) + hx,
            cy: f32::from(area.y0) + hy,
            sin,
            cos,
            bx: hx - radius,
            by: hy - radius,
            radius,
            scale: 1.0 / (sin.abs() + cos.abs()),
        }
    }

    /// Smallest rectangle containing all pixels with a non-zero coverage.
    fn bounds(&self) -> Rect {
        let (s, c) = (self.sin.abs(), self.cos.abs());
        // Antialiased pixels reach up to 0.5 / scale beyond the edge
        let ex = self.bx * c + self.by * s + self.radius + 0.5 / self.scale;
        let ey = self.bx * s + self.by * c + self.radius + 0.5 / self.scale;
        Rect::new(
            Point::new(floor_i16(self.cx - ex), floor_i16(self.cy - ey)),
            Point::new(floor_i16(self.cx + ex) + 1, floor_i16(self.cy + ey) + 1),
        )
    }

    /// Coordinates `(u0, v0)` of row `y` in the box's frame: the center of
    /// pixel `(x, y)` lies at `(u0 + cos * x, v0 - sin * x)`.
    fn row(&self, y: i16) -> (f32, f32) {
        let px = 0.5 - self.cx;
        let py = f32::from(y) + 0.5 - self.cy;
        (self.cos * px + self.sin * py, self.cos * py - self.sin * px)
    }

    /// Scaled distance of the point `(u, v)` given in the box's frame from
    /// the shape edge. Since `scale <= 1`, it never exceeds the true
    /// distance.
    fn dist(&self, u: f32, v: f32) -> f32 {
        let qx = u.abs() - self.bx;
        let qy = v.abs() - self.by;
        let d = if qx > 0.0 && qy > 0.0 {
            // Next to a rounded corner
            sqrt_f32(qx * qx + qy * qy)
        } else {
            qx.max(qy)
        };
        (d - self.radius) * self.scale
    }

    /// Scaled distance (see `dist()`) together with its derivative along
    /// the x axis.
    fn dist_grad(&self, u: f32, v: f32) -> (f32, f32) {
        let qx = u.abs() - self.bx;
        let qy = v.abs() - self.by;
        // Derivatives of qx, qy along the x axis
        let gx = if u < 0.0 { -self.cos } else { self.cos };
        let gy = if v < 0.0 { self.sin } else { -self.sin };

        let (d, g) = if qx > 0.0 && qy > 0.0 {
            // Next to a rounded corner
            let len = sqrt_f32(qx * qx + qy * qy);
            (len, (qx * gx + qy * gy) / len)
        } else if qx > qy {
            // Next to (or inside, closer to) a vertical side
            (qx, gx)
        } else {
            (qy, gy)
        };
        ((d - self.radius) * self.scale, g * self.scale)
    }
}

/// A single row of the rendered shape.
struct Row<'a> {
    sdf: &'a RoundBoxSdf,
    y: i16,
    /// The row in the box's frame, see `RoundBoxSdf::row()`
    u0: f32,
    v0: f32,
    /// Visible columns (`x1` exclusive)
    x0: i16,
    x1: i16,
    color: Color,
    alpha: u8,
}

impl Row<'_> {
    /// Draws the part of the row covered by the shape inset by `inset`
    /// pixels. If `hole` is set, the shape inset by `hole` pixels is left
    /// out (used for outlines).
    fn draw(&self, canvas: &mut dyn Canvas, inset: f32, hole: Option<f32>) {
        let outer_grad = |x| {
            let (d, g) = self.dist_grad(x);
            (d + inset, g)
        };
        let cov = |d: f32| {
            let c = coverage(d + inset);
            match hole {
                Some(h) => c - coverage(d + h),
                None => c,
            }
        };

        // Outer extent of the row
        let Some(l) = self.scan(self.x0, self.x1, 1, outer_grad) else {
            return;
        };
        let r = unwrap!(self.scan(self.x1 - 1, l - 1, -1, outer_grad));

        // Antialiased edges, the shape is convex so all pixels between
        // the edges are fully covered
        let ls = self.edge(canvas, l, r, 1, inset, cov);
        let rs = self.edge(canvas, r, ls, -1, inset, cov);
        if ls > rs {
            return;
        }

        let Some(h) = hole else {
            self.fill(canvas, ls, rs + 1);
            return;
        };

        // Extent of the hole inside the solid span
        let inner_grad = |x| {
            let (d, g) = self.dist_grad(x);
            (d + h, g)
        };
        let Some(li) = self.scan(ls, rs + 1, 1, inner_grad) else {
            self.fill(canvas, ls, rs + 1);
            return;
        };
        let ri = unwrap!(self.scan(rs, li - 1, -1, inner_grad));
        self.fill(canvas, ls, li);
        self.fill(canvas, ri + 1, rs + 1);

        // Antialiased inner edges, the hole is left untouched
        let a = self.edge(canvas, li, ri, 1, h, cov);
        self.edge(canvas, ri, a, -1, h, cov);
    }

    /// Blends pixels from `from` towards `last` (inclusive, walking by
    /// `step`) until reaching one fully covered by the shape inset by
    /// `inset`, which is returned. Pixels are blended with `cov(dist)`.
    fn edge(
        &self,
        canvas: &mut dyn Canvas,
        from: i16,
        last: i16,
        step: i16,
        inset: f32,
        cov: impl Fn(f32) -> f32,
    ) -> i16 {
        let mut x = from;
        while (step > 0 && x <= last) || (step < 0 && x >= last) {
            let d = self.dist(x);
            if coverage(d + inset) >= 1.0 {
                break;
            }
            self.blend(canvas, x, cov(d));
            x += step;
        }
        x
    }

    /// Returns the first pixel in `from..to` (walking by `step`) with
    /// non-zero coverage by `dist`, which returns the distance and its
    /// derivative along the x axis.
    ///
    /// The distance of a convex shape is a convex function, so along the
    /// row it never drops below its tangent. Pixels before the tangent
    /// reaches 0.5 cannot be covered and are skipped without evaluation,
    /// and if the distance is not decreasing, no pixel ahead is covered.
    fn scan(&self, from: i16, to: i16, step: i16, dist: impl Fn(i16) -> (f32, f32)) -> Option<i16> {
        let mut x = from;
        while (step > 0 && x < to) || (step < 0 && x > to) {
            let (t, g) = dist(x);
            if coverage(t) > 0.0 {
                return Some(x);
            }
            // Slope of the distance in the direction of the walk
            let slope = -g * f32::from(step);
            if t >= 0.5 && slope <= 0.0 {
                return None;
            }
            let skip = if t >= 0.5 {
                ((t - 0.5) / slope) as i16 + 1
            } else {
                1
            };
            x = x.saturating_add(step.saturating_mul(skip));
        }
        None
    }

    /// Distance of pixel `x` of the row, see `RoundBoxSdf::dist()`.
    fn dist(&self, x: i16) -> f32 {
        let x = f32::from(x);
        self.sdf
            .dist(self.u0 + self.sdf.cos * x, self.v0 - self.sdf.sin * x)
    }

    /// Distance of pixel `x` of the row with its derivative, see
    /// `RoundBoxSdf::dist_grad()`.
    fn dist_grad(&self, x: i16) -> (f32, f32) {
        let x = f32::from(x);
        self.sdf
            .dist_grad(self.u0 + self.sdf.cos * x, self.v0 - self.sdf.sin * x)
    }

    /// Fills the fully covered pixels `x0..x1`.
    fn fill(&self, canvas: &mut dyn Canvas, x0: i16, x1: i16) {
        if x1 - x0 > MAX_CPU_SPAN {
            let r = Rect::new(Point::new(x0, self.y), Point::new(x1, self.y + 1));
            canvas.fill_rect(r, self.color, self.alpha);
        } else if self.alpha == 255 {
            for x in x0..x1 {
                canvas.draw_pixel(Point::new(x, self.y), self.color);
            }
        } else {
            for x in x0..x1 {
                canvas.blend_pixel(Point::new(x, self.y), self.color, self.alpha);
            }
        }
    }

    fn blend(&self, canvas: &mut dyn Canvas, x: i16, cov: f32) {
        let alpha = (cov * f32::from(self.alpha) + 0.5) as u8;
        if alpha > 0 {
            canvas.blend_pixel(Point::new(x, self.y), self.color, alpha);
        }
    }
}

/// Pixel coverage <0..1> by a shape whose edge is `dist` pixels away
/// from the pixel center.
#[cfg(feature = "ui_antialiasing")]
fn coverage(dist: f32) -> f32 {
    (0.5 - dist).clamp(0.0, 1.0)
}

#[cfg(not(feature = "ui_antialiasing"))]
fn coverage(dist: f32) -> f32 {
    if dist <= 0.0 {
        1.0
    } else {
        0.0
    }
}

fn floor_i16(v: f32) -> i16 {
    let t = v as i16;
    if f32::from(t) > v {
        t - 1
    } else {
        t
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ui::geometry::Offset;
    use crate::ui::shape::{BasicCanvas, Mono8Canvas, Viewport};

    const SIZE: i16 = 100;

    /// Allowed deviation of the covered area in pixels.
    #[cfg(feature = "ui_antialiasing")]
    const TOLERANCE: f32 = 1.5;
    /// Without antialiasing, pixel centers lying exactly on 45-degree edges
    /// are all counted in.
    #[cfg(not(feature = "ui_antialiasing"))]
    const TOLERANCE: f32 = 25.0;

    fn render(bar: RotatedBar, slice: Option<i16>) -> [u8; (SIZE * SIZE) as usize] {
        let mut buf = [0u8; (SIZE * SIZE) as usize];
        {
            let mut canvas = unwrap!(Mono8Canvas::new(
                Offset::new(SIZE, SIZE),
                None,
                None,
                &mut buf[..]
            ));
            canvas.fill_background(Color::black());
            match slice {
                None => bar.draw_on(&mut canvas),
                Some(h) => {
                    for y in (0..SIZE).step_by(h as usize) {
                        let clip = Rect::new(Point::new(0, y), Point::new(SIZE, y + h));
                        canvas.set_viewport(Viewport::new(clip));
                        bar.draw_on(&mut canvas);
                    }
                }
            }
        }
        buf
    }

    /// Covered area in pixels.
    ///
    /// Mono8 `blend_pixel()` saturates at the luminance of white (248),
    /// while `fill_rect()` writes 255, so both count as full coverage.
    fn area(buf: &[u8]) -> f32 {
        let white = Color::white().luminance() as u8;
        buf.iter().map(|&p| f32::from(p.min(white))).sum::<f32>() / f32::from(white)
    }

    fn rect(w: i16, h: i16) -> Rect {
        Rect::from_center_and_size(Point::new(SIZE / 2, SIZE / 2), Offset::new(w, h))
    }

    fn round_box_area(w: f32, h: f32, r: f32) -> f32 {
        w * h - (4.0 - core::f32::consts::PI) * r * r
    }

    #[test]
    fn filled_area() {
        for angle in [0.0, 7.0, 30.0, 45.0, 90.0, 133.0, -20.0] {
            let bar = RotatedBar::new(rect(60, 40))
                .with_bg(Color::white())
                .with_radius(10)
                .with_angle(angle);
            let a = area(&render(bar, None));
            let expected = round_box_area(60.0, 40.0, 10.0);
            assert!(
                (a - expected).abs() < TOLERANCE,
                "angle {}: {} vs {}",
                angle,
                a,
                expected
            );
        }
    }

    #[test]
    fn outline_area() {
        for angle in [0.0, 12.5, 45.0, 200.0] {
            let bar = RotatedBar::new(rect(60, 40))
                .with_fg(Color::white())
                .with_thickness(3)
                .with_radius(10)
                .with_angle(angle);
            let a = area(&render(bar, None));
            let expected = round_box_area(60.0, 40.0, 10.0) - round_box_area(54.0, 34.0, 7.0);
            assert!(
                (a - expected).abs() < TOLERANCE,
                "angle {}: {} vs {}",
                angle,
                a,
                expected
            );
        }
    }

    #[test]
    fn quarter_turn_is_exact() {
        let wide = RotatedBar::new(rect(60, 40))
            .with_bg(Color::white())
            .with_radius(8)
            .with_angle(90.0);
        let tall = RotatedBar::new(rect(40, 60))
            .with_bg(Color::white())
            .with_radius(8);
        assert!(render(wide, None) == render(tall, None));
    }

    #[test]
    fn sliced_rendering_matches() {
        for angle in [0.0, 17.0, 60.0] {
            let bar = || {
                RotatedBar::new(rect(70, 30))
                    .with_fg(Color::white())
                    .with_thickness(2)
                    .with_radius(12)
                    .with_angle(angle)
            };
            assert!(render(bar(), None) == render(bar(), Some(3)));
        }
    }
}
