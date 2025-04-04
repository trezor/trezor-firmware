use crate::{
    io::BinaryData,
    ui::{
        display::image::JpegInfo,
        geometry::{Alignment2D, Offset, Point, Rect},
    },
};

use super::{Canvas, DrawingCache, Renderer, Shape, ShapeClone};

use crate::{trezorhal::jpegdec::JpegDecoder, ui::display::Color};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for rendering grayscale JPEG images as a transparent overlay
/// over the existing content.
pub struct JpegOverlay<'a> {
    /// Image position
    pos: Point,
    // Image position alignment
    align: Alignment2D,
    /// JPEG data
    jpeg: BinaryData<'a>,
    /// Color of the overlay (default white)
    fg_color: Color,
    /// Alpha in range of 0..255 (default 255)
    alpha: u8,
    /// Final size calculated from JPEG headers
    size: Offset,
}

impl<'a> JpegOverlay<'a> {
    pub fn new_image(pos: Point, jpeg: BinaryData<'a>) -> Self {
        JpegOverlay {
            pos,
            align: Alignment2D::TOP_LEFT,
            jpeg,
            fg_color: Color::white(),
            alpha: 255,
            size: Offset::zero(),
        }
    }

    pub fn new(pos: Point, jpeg: &'a [u8]) -> Self {
        Self::new_image(pos, jpeg.into())
    }

    pub fn with_align(self, align: Alignment2D) -> Self {
        Self { align, ..self }
    }

    pub fn with_fg(self, fg_color: Color) -> Self {
        Self { fg_color, ..self }
    }

    pub fn with_alpha(self, alpha: u8) -> Self {
        Self { alpha, ..self }
    }

    pub fn render(mut self, renderer: &mut impl Renderer<'a>) {
        self.size = self.calc_size();
        renderer.render_shape(self);
    }

    fn calc_size(&self) -> Offset {
        unwrap!(JpegInfo::parse(self.jpeg), "Invalid image").size()
    }
}

impl<'a> Shape<'a> for JpegOverlay<'a> {
    fn bounds(&self) -> Rect {
        Rect::from_top_left_and_size(self.size.snap(self.pos, self.align), self.size)
    }

    fn cleanup(&mut self, _cache: &DrawingCache<'a>) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache<'a>) {
        let bounds = self.bounds();
        let clip = canvas.viewport().relative_clip(bounds).clip;

        // Translate clip to JPEG relative coordinates
        let clip = clip.translate(-canvas.viewport().origin);
        let clip = clip.translate((-bounds.top_left()).into());

        // Get temporary buffer for image decoding
        let buff = &mut unwrap!(cache.image_buff(), "No image buffer");

        let mut jpegdec = unwrap!(JpegDecoder::new(self.jpeg));
        let _ = jpegdec.decode_mono8(&mut buff[..], &mut |slice_r, slice| {
            let slice = slice.with_fg(self.fg_color).with_alpha(self.alpha);
            // Draw single slice
            canvas.blend_bitmap(slice_r.translate(bounds.top_left().into()), slice);
            // Return true if we are not done yet
            slice_r.x1 < clip.x1 || slice_r.y1 < clip.y1
        });
    }
}

impl<'a> ShapeClone<'a> for JpegOverlay<'a> {
    fn clone_at_bump<T>(self, bump: &'a T) -> Option<&'a mut dyn Shape<'a>>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(JpegOverlay { ..self }))
    }
}
