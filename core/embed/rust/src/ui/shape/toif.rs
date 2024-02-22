use crate::ui::{
    canvas::{Bitmap, BitmapFormat, Canvas},
    display::{toif::Toif, Color},
    geometry::{Alignment2D, Offset, Point, Rect},
};

use super::{DrawingCache, Renderer, Shape, ShapeClone};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for rendering compressed TOIF images.
pub struct ToifImage<'a> {
    /// Image position
    pos: Point,
    // Image position alignment
    align: Alignment2D,
    // Image data
    toif: Toif<'a>,
    // Foreground color
    fg_color: Color,
    // Optional background color
    bg_color: Option<Color>,
}

impl<'a> ToifImage<'a> {
    pub fn new(pos: Point, toif: Toif<'a>) -> Self {
        Self {
            pos,
            align: Alignment2D::TOP_LEFT,
            toif,
            fg_color: Color::white(),
            bg_color: None,
        }
    }

    pub fn with_align(self, align: Alignment2D) -> Self {
        Self { align, ..self }
    }

    pub fn with_fg(self, fg_color: Color) -> Self {
        Self { fg_color, ..self }
    }

    pub fn with_bg(self, bg_color: Color) -> Self {
        Self {
            bg_color: Some(bg_color),
            ..self
        }
    }

    pub fn render(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }

    fn draw_grayscale(&self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        // TODO: introduce new viewport/shape function for this calculation
        let bounds = self.bounds(cache);
        let viewport = canvas.viewport();
        let mut clip = self
            .bounds(cache)
            .intersect(viewport.clip.translate(-viewport.origin))
            .translate((-bounds.top_left()).into());

        let buff = &mut unwrap!(cache.image_buff(), "No image buffer");
        let mut slice = unwrap!(
            Bitmap::new_mut(
                BitmapFormat::MONO4,
                None,
                self.toif.size(),
                Some(1),
                &mut buff[..]
            ),
            "Too small buffer"
        );

        while !clip.is_empty() {
            let height = core::cmp::min(slice.height(), clip.height());
            unwrap!(
                cache.zlib().uncompress_toif(
                    self.toif,
                    clip.y0,
                    unwrap!(slice.rows_mut(0, height)), // should never fail
                ),
                "Invalid TOIF"
            );

            let r = clip.translate(bounds.top_left().into());

            let slice_view = slice
                .view()
                .with_fg(self.fg_color)
                .with_offset(Offset::new(r.x0 - bounds.top_left().x, 0));

            match self.bg_color {
                Some(bg_color) => canvas.draw_bitmap(r, slice_view.with_bg(bg_color)),
                None => canvas.blend_bitmap(r, slice_view),
            }

            clip.y0 += height;
        }
    }

    fn draw_rgb(&self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        // TODO: introduce new viewport/shape function for this calculation
        let bounds = self.bounds(cache);
        let viewport = canvas.viewport();
        let mut clip = self
            .bounds(cache)
            .intersect(viewport.clip.translate(-viewport.origin))
            .translate((-bounds.top_left()).into());

        let buff = &mut unwrap!(cache.image_buff(), "No image buffer");
        let mut slice = unwrap!(
            Bitmap::new_mut(
                BitmapFormat::RGB565,
                None,
                self.toif.size(),
                Some(1),
                &mut buff[..]
            ),
            "Too small buffer"
        );

        while !clip.is_empty() {
            let height = core::cmp::min(slice.height(), clip.height());

            if let Some(row_bytes) = slice.rows_mut(0, height) {
                // always true
                unwrap!(
                    cache.zlib().uncompress_toif(self.toif, clip.y0, row_bytes,),
                    "Invalid TOIF"
                );
            }

            let r = clip.translate(bounds.top_left().into());

            let slice_view = slice
                .view()
                .with_offset(Offset::new(r.x0 - bounds.top_left().x, 0));

            canvas.draw_bitmap(r, slice_view);

            clip.y0 += height;
        }
    }
}

impl<'a> Shape<'a> for ToifImage<'a> {
    fn bounds(&self, _cache: &DrawingCache<'a>) -> Rect {
        let size = Offset::new(self.toif.width(), self.toif.height());
        Rect::from_top_left_and_size(size.snap(self.pos, self.align), size)
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {
        // TODO: inform the cache that we won't use the zlib slot anymore
    }

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        if self.toif.is_grayscale() {
            self.draw_grayscale(canvas, cache);
        } else {
            self.draw_rgb(canvas, cache);
        }
    }
}

impl<'a> ShapeClone<'a> for ToifImage<'a> {
    fn clone_at_bump<'alloc, T>(self, bump: &'alloc T) -> Option<&'alloc mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let clone = bump.alloc_t::<ToifImage>()?;
        Some(clone.uninit.init(ToifImage { ..self }))
    }
}
