use crate::ui::{
    display::Color,
    geometry::{Point, Rect},
};

use super::{Canvas, DrawingCache, Renderer, Shape, ShapeClone};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for rendering various types of circles or circle sectors.
pub struct Circle {
    center: Point,
    radius: i16,
    fg_color: Option<Color>,
    bg_color: Option<Color>,
    thickness: i16,
    start_angle: Option<i16>,
    end_angle: Option<i16>,
}

impl Circle {
    pub fn new(center: Point, radius: i16) -> Self {
        Self {
            center,
            radius,
            fg_color: None,
            bg_color: None,
            thickness: 1,
            start_angle: None,
            end_angle: None,
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

    pub fn with_thickness(self, thickness: i16) -> Self {
        Self { thickness, ..self }
    }

    pub fn with_start_angle(self, from_angle: i16) -> Self {
        Self {
            start_angle: Some(from_angle),
            ..self
        }
    }

    pub fn with_end_angle(self, to_angle: i16) -> Self {
        Self {
            end_angle: Some(to_angle),
            ..self
        }
    }

    pub fn render<'s>(self, renderer: &mut impl Renderer<'s>) {
        renderer.render_shape(self);
    }
}

impl Shape<'_> for Circle {
    fn bounds(&self, _cache: &DrawingCache) -> Rect {
        let c = self.center;
        let r = self.radius;
        Rect::new(
            Point::new(c.x - r, c.y - r),
            Point::new(c.x + r + 1, c.y + r + 1),
        )
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache) {
        // NOTE: drawing of circles without a background and with a thickness > 1
        //       is not supported. If we needed it, we would have to
        //       introduce RgbCanvas::draw_ring() function.

        // TODO: panic! in unsupported scenarious
        let th = match self.fg_color {
            Some(_) => self.thickness,
            None => 0,
        };

        if self.start_angle.is_none() && self.end_angle.is_none() {
            if th == 1 {
                if let Some(color) = self.bg_color {
                    canvas.fill_circle(self.center, self.radius, color);
                }
                if let Some(color) = self.fg_color {
                    #[cfg(not(feature = "ui_antialiasing"))]
                    canvas.draw_circle(self.center, self.radius, color);
                    #[cfg(feature = "ui_antialiasing")]
                    canvas.fill_circle(self.center, self.radius, color);
                }
            } else {
                if let Some(color) = self.fg_color {
                    if th > 0 {
                        canvas.fill_circle(self.center, self.radius, color);
                    }
                }
                if let Some(color) = self.bg_color {
                    canvas.fill_circle(self.center, self.radius - th, color);
                }
            }
        } else {
            let start = self.start_angle.unwrap_or(0);
            let end = self.end_angle.unwrap_or(360);

            if let Some(color) = self.fg_color {
                if th > 0 {
                    canvas.fill_sector(self.center, self.radius, start, end, color);
                }
            }
            if let Some(color) = self.bg_color {
                canvas.fill_sector(self.center, self.radius - th, start, end, color);
            }
        }
    }
}

impl<'s> ShapeClone<'s> for Circle {
    fn clone_at_bump<'alloc, T>(self, bump: &'alloc T) -> Option<&'alloc mut dyn Shape<'s>>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let clone = bump.alloc_t::<Circle>()?;
        Some(clone.uninit.init(Circle { ..self }))
    }
}
