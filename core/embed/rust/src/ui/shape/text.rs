use crate::ui::{
    display::{Color, Font},
    geometry::{Alignment, Offset, Point, Rect},
};

use super::{BitmapView, Canvas, DrawingCache, Renderer, Shape, ShapeClone};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for text strings rendering.
pub struct Text<'a> {
    // Text position
    pos: Point,
    // Text string
    text: &'a str,
    // Text color
    color: Color,
    // Text alpha
    alpha: u8,
    // Text font
    font: Font,
    // Horizontal alignment
    align: Alignment,
    // Final bounds calculated when rendered
    bounds: Rect,
}

impl<'a> Text<'a> {
    /// Creates a `shape::Text` structure with a specified
    /// text (`str`) and the bottom-left corner (`pos`).
    pub fn new(pos: Point, text: &'a str, font: Font) -> Self {
        Self {
            pos,
            text,
            color: Color::white(),
            alpha: 255,
            font,
            align: Alignment::Start,
            bounds: Rect::zero(),
        }
    }

    pub fn with_fg(self, color: Color) -> Self {
        Self { color, ..self }
    }

    pub fn with_align(self, align: Alignment) -> Self {
        Self { align, ..self }
    }

    pub fn with_alpha(self, alpha: u8) -> Self {
        Self { alpha, ..self }
    }

    pub fn render<'r>(mut self, renderer: &mut impl Renderer<'r>) {
        self.bounds = self.calc_bounds();
        renderer.render_shape(self);
    }

    fn aligned_pos(&self) -> Point {
        match self.align {
            Alignment::Start => self.pos,
            Alignment::Center => Point::new(
                self.font.horz_center(self.pos.x, self.pos.x, self.text),
                self.pos.y,
            ),
            Alignment::End => Point::new(self.pos.x - self.font.text_width(self.text), self.pos.y),
        }
    }

    fn calc_bounds(&self) -> Rect {
        let pos = self.aligned_pos();
        let (ascent, descent) = self.font.visible_text_height_ex(self.text);
        Rect {
            x0: pos.x,
            y0: pos.y - ascent,
            x1: pos.x + self.font.text_width(self.text),
            y1: pos.y + descent,
        }
    }
}

impl<'a> Shape<'_> for Text<'a> {
    fn bounds(&self) -> Rect {
        self.bounds
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, _cache: &DrawingCache) {
        let mut r = self.bounds();
        let max_ascent = self.pos.y - r.y0;

        // TODO: optimize  text clipping, use canvas.viewport()

        self.font.with_glyph_data(|glyph_data| {
            for ch in self.text.chars() {
                if r.x0 >= r.x1 {
                    break;
                }

                let glyph = glyph_data.get_glyph(ch);
                let glyph_bitmap = glyph.bitmap();
                let glyph_view = BitmapView::new(&glyph_bitmap)
                    .with_alpha(self.alpha)
                    .with_fg(self.color)
                    .with_offset(Offset::new(
                        -glyph.bearing_x,
                        -(max_ascent - glyph.bearing_y),
                    ));

                canvas.blend_bitmap(r, glyph_view);
                r.x0 += glyph.adv;
            }
        });
    }
}

impl<'a, 's> ShapeClone<'s> for Text<'a> {
    fn clone_at_bump<T>(self, bump: &'s T) -> Option<&'s mut dyn Shape<'s>>
    where
        T: LocalAllocLeakExt<'s>,
    {
        let clone = bump.alloc_t()?;
        let text = bump.copy_str(self.text)?;
        Some(clone.uninit.init(Text { text, ..self }))
    }
}
