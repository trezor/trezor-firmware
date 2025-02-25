use crate::{
    io::BinaryData,
    ui::{
        display::image::JpegInfo,
        geometry::{Alignment2D, Offset, Point, Rect},
    },
};

use super::{Canvas, DrawingCache, Renderer, Shape, ShapeClone};

#[cfg(not(feature = "hw_jpeg_decoder"))]
use super::{Bitmap, BitmapFormat, BitmapView};

#[cfg(feature = "hw_jpeg_decoder")]
use crate::{trezorhal::jpegdec::JpegDecoder, ui::display::Color};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for rendering compressed JPEG images.
pub struct JpegImage<'a> {
    /// Image position
    pos: Point,
    // Image position alignment
    align: Alignment2D,
    /// JPEG data
    jpeg: BinaryData<'a>,
    /// Scale factor (default 0)
    scale: u8,
    /// Blurring radius or 0 if no blurring required (default 0)
    blur_radius: usize,
    /// Dimming of blurred image in range of 0..255 (default 255)
    dim: u8,
    /// Final size calculated from JPEG headers
    size: Offset,
    /// Set if blurring is pending
    /// (used only during image drawing).
    #[cfg(not(feature = "hw_jpeg_decoder"))]
    blur_tag: Option<u32>,
}

impl<'a> JpegImage<'a> {
    pub fn new_image(pos: Point, jpeg: BinaryData<'a>) -> Self {
        JpegImage {
            pos,
            align: Alignment2D::TOP_LEFT,
            jpeg,
            scale: 0,
            blur_radius: 0,
            dim: 255,

            size: Offset::zero(),
            #[cfg(not(feature = "hw_jpeg_decoder"))]
            blur_tag: None,
        }
    }

    pub fn new(pos: Point, jpeg: &'a [u8]) -> Self {
        Self::new_image(pos, jpeg.into())
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

    pub fn render(mut self, renderer: &mut impl Renderer<'a>) {
        self.size = self.calc_size();
        renderer.render_shape(self);
    }

    fn calc_size(&self) -> Offset {
        let info = unwrap!(JpegInfo::parse(self.jpeg), "Invalid image");
        let scale_factor = 1 << self.scale;
        let size = info.size();
        Offset::new(size.x / scale_factor, size.y / scale_factor)
    }
}

impl<'a> Shape<'a> for JpegImage<'a> {
    fn bounds(&self) -> Rect {
        Rect::from_top_left_and_size(self.size.snap(self.pos, self.align), self.size)
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {
        #[cfg(not(feature = "hw_jpeg_decoder"))]
        {
            self.blur_tag = None;
        }
    }

    #[cfg(feature = "hw_jpeg_decoder")]
    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        let bounds = self.bounds();
        let clip = canvas.viewport().relative_clip(bounds).clip;

        // Translate clip to JPEG relative coordinates
        let clip = clip.translate(-canvas.viewport().origin);
        let clip = clip.translate((-bounds.top_left()).into());

        // Get temporary buffer for image decoding
        let buff = &mut unwrap!(cache.image_buff(), "No image buffer");

        let mut jpegdec = unwrap!(JpegDecoder::new(self.jpeg));
        let _ = jpegdec.decode(&mut buff[..], &mut |slice_r, slice| {
            let slice = slice.with_downscale(self.scale);
            let slice_r = Rect {
                x0: slice_r.x0 >> self.scale,
                y0: slice_r.y0 >> self.scale,
                x1: slice_r.x1 >> self.scale,
                y1: slice_r.y1 >> self.scale,
            };
            // Draw single slice
            canvas.draw_bitmap(slice_r.translate(bounds.top_left().into()), slice);
            // Return true if we are not done yet
            slice_r.x1 < clip.x1 || slice_r.y1 < clip.y1
        });

        if self.dim < 255 {
            // Draw dimmed overlay.
            // This solution is suboptimal and might be replaced by
            // using faster alpha blending in the hardware.
            canvas.fill_rect(bounds, Color::black(), 255 - self.dim);
        }

        if self.blur_radius > 0 {
            // Blur the image
            canvas.blur_rect(bounds, self.blur_radius, cache);
        }
    }

    // This is a little bit slower implementation suitable for ProgressiveRenderer
    #[cfg(not(feature = "hw_jpeg_decoder"))]
    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        let bounds = self.bounds();
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
            let jpeg_size = self.bounds().size();

            // Get a single line working bitmap
            let buff = &mut unwrap!(cache.image_buff(), "No image buffer");
            let mut slice = unwrap!(
                Bitmap::new_mut(
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
                                blur.push(unwrap!(jpeg_slice.row::<u16>(y - row_r.y0)));
                            } else {
                                return true; // need more data
                            }
                        }

                        if let Some(y) = blur.pop_ready() {
                            blur.pop(unwrap!(slice.row_mut::<u16>(0)), Some(self.dim)); // should never fail
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
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(JpegImage { ..self }))
    }
}
