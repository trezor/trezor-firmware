use crate::ui::{
    canvas::Canvas,
    display::Color,
    geometry::{Insets, Rect},
};

use super::{DrawingCache, Renderer, Shape, ShapeClone};

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
}

impl Bar {
    pub fn new(area: Rect) -> Self {
        Self {
            area,
            fg_color: None,
            bg_color: None,
            thickness: 1,
            radius: 0,
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

    pub fn render(self, renderer: &mut impl Renderer) {
        renderer.render_shape(self);
    }
}

impl Shape for Bar {
    fn bounds(&self, _cache: &DrawingCache) -> Rect {
        self.area
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache) {
        // NOTE: drawing of rounded bars without a background
        //       is not supported. If we needed it, we would have to
        //       introduce a new function in RgbCanvas.

        // TODO: panic! in unsupported scenarious

        let th = match self.fg_color {
            Some(_) => self.thickness,
            None => 0,
        };

        if self.radius == 0 {
            if let Some(fg_color) = self.fg_color {
                // outline
                let r = self.area;
                canvas.fill_rect(Rect { y1: r.y0 + th, ..r }, fg_color);
                canvas.fill_rect(Rect { x1: r.x0 + th, ..r }, fg_color);
                canvas.fill_rect(Rect { x0: r.x1 - th, ..r }, fg_color);
                canvas.fill_rect(Rect { y0: r.y1 - th, ..r }, fg_color);
            }
            if let Some(bg_color) = self.bg_color {
                // background
                let bg_r = self.area.inset(Insets::uniform(th));
                canvas.fill_rect(bg_r, bg_color);
            }
        } else {
            if let Some(fg_color) = self.fg_color {
                if self.bg_color.is_some() {
                    canvas.fill_round_rect(self.area, self.radius, fg_color);
                } else {
                    #[cfg(not(feature = "ui_antialiasing"))]
                    canvas.draw_round_rect(self.area, self.radius, fg_color);
                }
            }
            if let Some(bg_color) = self.bg_color {
                let bg_r = self.area.inset(Insets::uniform(th));
                canvas.fill_round_rect(bg_r, self.radius, bg_color);
            }
        }
    }
}

impl ShapeClone for Bar {
    fn clone_at_bump<'alloc, T>(self, bump: &'alloc T) -> Option<&'alloc mut dyn Shape>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let clone = bump.alloc_t::<Bar>()?;
        Some(clone.uninit.init(Bar { ..self }))
    }
}
