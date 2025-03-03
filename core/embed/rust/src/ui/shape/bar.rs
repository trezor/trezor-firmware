use crate::ui::{display::Color, geometry::Rect};

use super::{Canvas, DrawingCache, Renderer, Shape, ShapeClone};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for the rendering variuous type of rectangles.
pub struct Bar {
    /// Rectangle position and dimenstion
    area: Rect,
    /// Foreground color (default None)
    fg_color: Option<Color>,
    /// Background color (default None)
    bg_color: Option<Color>,
    /// Thickness (default 0)
    thickness: i16,
    /// Corner radius (default 0)
    radius: i16,
    /// Alpha (default 255)
    alpha: u8,
}

impl Bar {
    pub fn new(area: Rect) -> Self {
        Self {
            area,
            fg_color: None,
            bg_color: None,
            thickness: 1,
            radius: 0,
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

    pub fn with_alpha(self, alpha: u8) -> Self {
        Self { alpha, ..self }
    }

    pub fn render<'s>(self, renderer: &mut impl Renderer<'s>) {
        renderer.render_shape(self);
    }
}

impl Shape<'_> for Bar {
    fn bounds(&self) -> Rect {
        self.area
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache) {
        // NOTE: drawing of rounded bars without a background
        //       is not supported. If we needed it, we would have to
        //       introduce a new function in RgbCanvas.

        // TODO: fatal_error! in unsupported scenarious

        let (fg_color, bg_color, th) = if self.fg_color.is_some() {
            let th = self.thickness;
            if th * 2 < self.area.width() && th * 2 < self.area.height() {
                // Draw a rectangle with a border
                (self.fg_color, self.bg_color, th)
            } else {
                // Too thick border => draw a filled rectangle
                (None, self.fg_color, 0)
            }
        } else {
            // No foreground color => draw a filled rectangle
            (None, self.bg_color, 0)
        };

        if self.radius == 0 {
            if let Some(fg_color) = fg_color {
                // outline
                if th > 0 {
                    let r = self.area;
                    // top
                    canvas.fill_rect(
                        Rect {
                            y1: r.y0 + th,
                            x1: r.x1 - th,
                            ..r
                        },
                        fg_color,
                        self.alpha,
                    );
                    // left
                    canvas.fill_rect(
                        Rect {
                            x1: r.x0 + th,
                            y0: r.y0 + th,
                            ..r
                        },
                        fg_color,
                        self.alpha,
                    );
                    // right
                    canvas.fill_rect(
                        Rect {
                            x0: r.x1 - th,
                            y1: r.y1 - th,
                            ..r
                        },
                        fg_color,
                        self.alpha,
                    );
                    // bottom
                    canvas.fill_rect(
                        Rect {
                            y0: r.y1 - th,
                            x0: r.x0 + th,
                            ..r
                        },
                        fg_color,
                        self.alpha,
                    );
                }
            }
            if let Some(bg_color) = bg_color {
                // background
                let bg_r = self.area.shrink(th);
                canvas.fill_rect(bg_r, bg_color, self.alpha);
            }
        } else {
            if let Some(fg_color) = fg_color {
                if th > 0 {
                    if self.bg_color.is_some() {
                        canvas.fill_round_rect(self.area, self.radius, fg_color, self.alpha);
                    } else {
                        #[cfg(not(feature = "ui_antialiasing"))]
                        canvas.draw_round_rect(self.area, self.radius, fg_color);
                    }
                }
            }
            if let Some(bg_color) = bg_color {
                let bg_r = self.area.shrink(th);
                canvas.fill_round_rect(bg_r, self.radius, bg_color, self.alpha);
            }
        }
    }
}

impl<'s> ShapeClone<'s> for Bar {
    fn clone_at_bump<T>(self, bump: &'s T) -> Option<&'s mut dyn Shape<'s>>
    where
        T: LocalAllocLeakExt<'s>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(Bar { ..self }))
    }
}
