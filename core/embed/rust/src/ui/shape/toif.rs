use crate::{
    io::BinaryData,
    ui::{
        display::{image::ToifInfo, toif::Toif, Color},
        geometry::{Alignment2D, Offset, Point, Rect},
    },
};

use super::{Bitmap, BitmapFormat, Canvas, DrawingCache, Renderer, Shape, ShapeClone};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for rendering compressed TOIF images.
pub struct ToifImage<'a> {
    /// Image position
    pos: Point,
    // Image position alignment
    align: Alignment2D,
    // Image data
    toif: BinaryData<'a>,
    // Foreground color
    fg_color: Color,
    // Optional background color
    bg_color: Option<Color>,
    // Alpha value
    alpha: u8,
    /// Final size calculated from TOIF data
    size: Offset,
    /// Whether to use caching
    use_cache: bool,
}

impl<'a> ToifImage<'a> {
    pub fn new_image(pos: Point, toif: BinaryData<'a>) -> Self {
        Self {
            pos,
            align: Alignment2D::TOP_LEFT,
            toif,
            fg_color: Color::white(),
            bg_color: None,
            alpha: 255,
            size: Offset::zero(),
            use_cache: false,
        }
    }

    pub fn new(pos: Point, toif: Toif<'a>) -> Self {
        Self {
            pos,
            align: Alignment2D::TOP_LEFT,
            toif: toif.original_data().into(),
            fg_color: Color::white(),
            bg_color: None,
            alpha: 255,
            size: Offset::zero(),
            use_cache: false,
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

    pub fn with_alpha(self, alpha: u8) -> Self {
        Self { alpha, ..self }
    }

    pub fn with_cache(self, use_cache: bool) -> Self {
        Self { use_cache, ..self }
    }

    pub fn render(mut self, renderer: &mut impl Renderer<'a>) {
        self.size = self.calc_size();
        renderer.render_shape(self);
    }

    fn draw_from_cache(&self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) -> bool {
        if !self.use_cache {
            return false;
        }

        let mut toif_cache = cache.toif_cache();
        let mut zlib_cache = cache.zlib();

        // Draw directly from cache to canvas
        toif_cache.draw_to_canvas(
            self.toif,
            canvas,
            self.bounds(),
            Some(self.fg_color),
            self.bg_color,
            self.alpha,
            &mut zlib_cache,
        )
    }

    fn draw_grayscale(&self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        // Check if we can use the cache
        if self.draw_from_cache(canvas, cache) {
            return;
        }

        // TODO: introduce new viewport/shape function for this calculation
        let bounds = self.bounds();
        let viewport = canvas.viewport();
        let mut clip = self
            .bounds()
            .clamp(viewport.clip.translate(-viewport.origin))
            .translate((-bounds.top_left()).into());

        let buff = &mut unwrap!(cache.image_buff(), "No image buffer");
        let mut slice = unwrap!(
            Bitmap::new_mut(
                BitmapFormat::MONO4,
                None,
                bounds.size(),
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
                .with_offset(Offset::new(r.x0 - bounds.top_left().x, 0))
                .with_alpha(self.alpha);

            match self.bg_color {
                Some(bg_color) => canvas.draw_bitmap(r, slice_view.with_bg(bg_color)),
                None => canvas.blend_bitmap(r, slice_view),
            }

            clip.y0 += height;
        }
    }

    fn draw_rgb(&self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        // Check if we can use the cache
        if self.draw_from_cache(canvas, cache) {
            return;
        }

        // TODO: introduce new viewport/shape function for this calculation
        let bounds = self.bounds();
        let viewport = canvas.viewport();
        let mut clip = self
            .bounds()
            .clamp(viewport.clip.translate(-viewport.origin))
            .translate((-bounds.top_left()).into());

        let buff = &mut unwrap!(cache.image_buff(), "No image buffer");
        let mut slice = unwrap!(
            Bitmap::new_mut(
                BitmapFormat::RGB565,
                None,
                bounds.size(),
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

    fn calc_size(&self) -> Offset {
        let info = unwrap!(ToifInfo::parse(self.toif), "Invalid image");
        info.size()
    }
}

impl<'a> Shape<'a> for ToifImage<'a> {
    fn bounds(&self) -> Rect {
        Rect::from_top_left_and_size(self.size.snap(self.pos, self.align), self.size)
    }

    fn cleanup(&mut self, cache: &DrawingCache<'a>) {
        // If we're using caching, release our reference when we're done
        if self.use_cache {
            cache.toif_cache().release(self.toif);
        }
        // TODO: inform the zlib cache that we won't use the zlib slot anymore
    }

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        let info = unwrap!(ToifInfo::parse(self.toif), "Invalid image");
        if info.is_grayscale() {
            self.draw_grayscale(canvas, cache);
        } else {
            self.draw_rgb(canvas, cache);
        }
    }
}

impl<'a> ShapeClone<'a> for ToifImage<'a> {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(ToifImage { ..self }))
    }
}
