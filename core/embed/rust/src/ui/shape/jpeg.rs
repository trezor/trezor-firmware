use crate::ui::geometry::{Alignment2D, Offset, Point, Rect};

use super::{Bitmap, BitmapFormat, BitmapView, Canvas, DrawingCache, Renderer, Shape, ShapeClone};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for rendering compressed JPEG images.
pub struct JpegImage<'a> {
    /// Image position
    pos: Point,
    // Image position alignment
    align: Alignment2D,
    /// JPEG data
    jpeg: &'a [u8],
    /// Scale factor (default 0)
    scale: u8,
    /// Blurring radius or 0 if no blurring required (default 0)
    blur_radius: usize,
    /// Dimming of blurred image in range of 0..255 (default 255)
    dim: u8,
    /// Set if blurring is pending
    /// (used only during image drawing).
    blur_tag: Option<u32>,
}

impl<'a> JpegImage<'a> {
    pub fn new(pos: Point, jpeg: &'a [u8]) -> Self {
        JpegImage {
            pos,
            align: Alignment2D::TOP_LEFT,
            scale: 0,
            dim: 255,
            blur_radius: 0,
            jpeg,
            blur_tag: None,
        }
    }

    pub fn with_align(self, align: Alignment2D) -> Self {
        Self { align, ..self }
    }

    pub fn with_scale(self, scale: u8) -> Self {
        assert!(scale <= 3);
        Self { scale, ..self }
    }

    pub fn with_blur(self, blur_radius: usize) -> Self {
        Self {
            blur_radius,
            ..self
        }
    }

    pub fn with_dim(self, dim: u8) -> Self {
        Self { dim, ..self }
    }

    pub fn render(self, renderer: &mut impl Renderer<'a>) {
        renderer.render_shape(self);
    }
}

impl<'a> Shape<'a> for JpegImage<'a> {
    fn bounds(&self, cache: &DrawingCache<'a>) -> Rect {
        let size = unwrap!(cache.jpeg().get_size(self.jpeg, self.scale), "Invalid JPEG");
        Rect::from_top_left_and_size(size.snap(self.pos, self.align), size)
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {
        self.blur_tag = None;
    }

    /*
    // Faster implementation suitable for DirectRenderer without blurring support
    // (but is terribly slow on ProgressiveRenderer if slices are not aligned
    //  to JPEG MCUs )
    fn draw(&mut self, canvas: &mut dyn RgbCanvasEx, cache: &DrawingCache<'a>) {
        let bounds = self.bounds(cache);
        let clip = canvas.viewport().relative_clip(bounds).clip;

        // translate clip to JPEG relative coordinates
        let clip = clip.translate(-canvas.viewport().origin);
        let clip = clip.translate((-bounds.top_left()).into());

        unwrap!(
            cache.jpeg().decompress_mcu(
                self.jpeg,
                self.scale,
                clip.top_left(),
                &mut |mcu_r, mcu_bitmap| {
                    // Draw single MCU
                    canvas.draw_bitmap(mcu_r.translate(bounds.top_left().into()), mcu_bitmap);
                    // Return true if we are not done yet
                    mcu_r.x1 < clip.x1 || mcu_r.y1 < clip.y1
                }
            ),
            "Invalid JPEG"
        );
    }*/

    // This is a little bit slower implementation suitable for ProgressiveRenderer
    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        let bounds = self.bounds(cache);
        let clip = canvas.viewport().relative_clip(bounds).clip;

        // Translate clip to JPEG relative coordinates
        let clip = clip.translate(-canvas.viewport().origin);
        let clip = clip.translate((-bounds.top_left()).into());

        if self.blur_radius == 0 {
            // Draw JPEG without blurring

            // Routine for drawing single JPEG MCU
            let draw_mcu = &mut |row_r: Rect, row_bitmap: BitmapView| {
                // Draw a row of decoded MCUs
                canvas.draw_bitmap(row_r.translate(bounds.top_left().into()), row_bitmap);
                // Return true if we are not done yet
                row_r.y1 < clip.y1
            };

            unwrap!(
                cache
                    .jpeg()
                    .decompress_row(self.jpeg, self.scale, clip.y0, draw_mcu),
                "Invalid JPEG"
            );
        } else {
            // Draw JPEG with blurring effect
            let jpeg_size = self.bounds(cache).size();

            // Get a single line working bitmap
            let buff = &mut unwrap!(cache.image_buff(), "No image buffer");
            let mut slice = unwrap!(
                Bitmap::new(
                    BitmapFormat::RGB565,
                    None,
                    Offset::new(jpeg_size.x, 1),
                    None,
                    &mut buff[..]
                ),
                "Too small buffer"
            );

            // Get the blurring algorithm instance
            let mut blur_cache = cache.blur();
            let (blur, blur_tag) =
                unwrap!(blur_cache.get(jpeg_size, self.blur_radius, self.blur_tag));
            self.blur_tag = Some(blur_tag);

            if let Some(y) = blur.push_ready() {
                // A function for drawing a row of JPEG MCUs
                let draw_row = &mut |row_r: Rect, jpeg_slice: BitmapView| {
                    loop {
                        if let Some(y) = blur.push_ready() {
                            if y < row_r.y1 {
                                // should never fail
                                blur.push(unwrap!(jpeg_slice.row(y - row_r.y0)));
                            } else {
                                return true; // need more data
                            }
                        }

                        if let Some(y) = blur.pop_ready() {
                            blur.pop(unwrap!(slice.row_mut(0)), Some(self.dim)); // should never fail
                            let dst_r = Rect::from_top_left_and_size(bounds.top_left(), jpeg_size)
                                .translate(Offset::new(0, y));
                            canvas.draw_bitmap(dst_r, slice.view());

                            if y + 1 >= clip.y1 {
                                return false; // we are done
                            }
                        }
                    }
                };

                unwrap!(
                    cache
                        .jpeg()
                        .decompress_row(self.jpeg, self.scale, y, draw_row),
                    "Invalid JPEG"
                );
            }
        }
    }
}

impl<'a> ShapeClone<'a> for JpegImage<'a> {
    fn clone_at_bump<'alloc, T>(self, bump: &'alloc T) -> Option<&'alloc mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let clone = bump.alloc_t::<JpegImage>()?;
        Some(clone.uninit.init(JpegImage { ..self }))
    }
}
