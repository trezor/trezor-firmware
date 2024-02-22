use crate::ui::{
    canvas::{BitmapView, Canvas},
    display::{Color, Font},
    geometry::{Alignment, Alignment2D, Offset, Point, Rect},
};

use super::{DrawingCache, Renderer, Shape, ShapeClone};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for text strings rendering.
pub struct Text<'a> {
    // Text position
    pos: Point,
    // Text string
    text: &'a str,
    // Text color
    color: Color,
    // Text font
    font: Font,
    // Horizontal alignment
    align: Alignment,
    // Vertical alignment
    baseline: bool,
}

impl<'a> Text<'a> {
    /// Creates a `shape::Text` structure with a specified
    /// text (`str`) and the top-left corner (`pos`).
    pub fn new(pos: Point, text: &'a str) -> Self {
        Self {
            pos,
            text,
            color: Color::white(),
            font: Font::NORMAL,
            align: Alignment::Start,
            baseline: true,
        }
    }

    pub fn with_fg(self, color: Color) -> Self {
        Self { color, ..self }
    }

    pub fn with_font(self, font: Font) -> Self {
        Self { font, ..self }
    }

    pub fn with_align(self, align: Alignment) -> Self {
        Self { align, ..self }
    }

    pub fn with_baseline(self, baseline: bool) -> Self {
        Self { baseline, ..self }
    }

    pub fn render(self, renderer: &mut impl Renderer) {
        renderer.render_shape(self);
    }
}

impl<'a> Shape for Text<'a> {
    fn bounds(&self, _cache: &DrawingCache) -> Rect {
        let w = self.font.text_width(self.text);
        let h = self.font.text_max_height();
        let ofs = if self.baseline {
            Offset::y(self.font.text_max_height() - self.font.text_baseline())
        } else {
            Offset::zero()
        };
        let size = Offset::new(w, h);
        Rect::from_top_left_and_size(
            size.snap(self.pos, Alignment2D(self.align, Alignment::Start)) - ofs,
            size,
        )
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache) {
        let max_height = self.font.max_height();
        let baseline = self.font.text_baseline();
        let mut r = self.bounds(cache);

        // TODO: optimize  text clipping, use canvas.viewport()

        for ch in self.text.chars() {
            if r.x0 >= r.x1 {
                break;
            }

            let glyph = self.font.get_glyph(ch);
            let glyph_bitmap = glyph.bitmap();
            let glyph_view = BitmapView::new(&glyph_bitmap)
                .with_fg(self.color)
                .with_offset(Offset::new(
                    -glyph.bearing_x,
                    -(max_height - baseline - glyph.bearing_y),
                ));

            canvas.blend_bitmap(r, glyph_view);
            r.x0 += glyph.adv;
        }
    }
}

impl<'a> ShapeClone for Text<'a> {
    fn clone_at_bump<'alloc, T>(self, bump: &'alloc T) -> Option<&'alloc mut dyn Shape>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let clone = bump.alloc_t::<Text>()?;
        let text = bump.copy_str(self.text)?;
        Some(clone.uninit.init(Text { text, ..self }))
    }
}
