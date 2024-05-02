use super::ffi;

use crate::ui::{
    display::Color,
    geometry::Rect,
    shape::{Bitmap, BitmapFormat, BitmapView},
};

pub type BitBlt = ffi::gl_bitblt_t;

impl Default for BitBlt {
    fn default() -> Self {
        Self {
            width: 0,
            height: 0,
            dst_row: core::ptr::null_mut(),
            dst_stride: 0,
            dst_x: 0,
            dst_y: 0,
            src_row: core::ptr::null_mut(),
            src_bg: 0,
            src_fg: 0,
            src_stride: 0,
            src_x: 0,
            src_y: 0,
            src_alpha: 255,
        }
    }
}

impl BitBlt {
    /// Sets the destination bitmap.
    ///
    /// Be sure that clipping rectangle specified in the `new_fill()` or
    /// `new_copy()` method is completely inside the destination bitmap.
    fn with_dst(self, dst: &mut Bitmap) -> Self {
        // Ensure that the destination rectangle is completely inside the
        // destination bitmap.
        assert!(dst.width() as u16 >= self.dst_x + self.width);
        assert!(dst.height() as u16 >= self.dst_y + self.height);

        Self {
            // SAFETY:
            // Lines between `dst_y` and`dst_y + height` are inside
            // the destination bitmap.
            dst_row: unsafe { dst.row_ptr(self.dst_y) },
            dst_stride: dst.stride() as u16,
            ..self
        }
    }

    // Sets the destination rectangle.
    fn with_rect(self, r: Rect) -> Self {
        Self {
            width: r.width() as u16,
            height: r.height() as u16,
            dst_x: r.x0 as u16,
            dst_y: r.y0 as u16,
            ..self
        }
    }

    /// Sets the source bitmap
    ///
    /// `x` and `y` specify the offset applied to the source bitmap and
    /// must be inside the source bitmap.
    fn with_src(self, bitmap: &Bitmap, x: i16, y: i16) -> Self {
        let bitmap_stride = match bitmap.format() {
            BitmapFormat::MONO1P => bitmap.width() as u16, // packed bits
            _ => bitmap.stride() as u16,
        };

        Self {
            // SAFETY:
            // it's safe if the functions the source rectangle is
            // properly clipped what's ensured by the `BitBltCopy::new()` method.
            src_row: unsafe { bitmap.row_ptr(y as u16) },
            src_stride: bitmap_stride,
            src_x: x as u16,
            src_y: y as u16,
            ..self
        }
    }

    /// Sets foreground color used for rectangle filling or
    /// drawing monochrome bitmaps.
    fn with_fg(self, fg_color: Color) -> Self {
        Self {
            src_fg: fg_color.into(),
            ..self
        }
    }

    /// Sets foreground color used for drawing monochrome bitmaps.
    fn with_bg(self, bg_color: Color) -> Self {
        Self {
            src_bg: bg_color.into(),
            ..self
        }
    }

    /// Sets the foreground alpha value used for rectangle filling or
    /// bitmap blending.
    fn with_alpha(self, alpha: u8) -> Self {
        Self {
            src_alpha: alpha,
            ..self
        }
    }

    /// Waits for the DMA2D peripheral transfer to complete.
    pub fn wait_for_transfer() {
        // SAFETY:
        // `ffi::dma2d_wait()` is always safe to call.
        #[cfg(feature = "dma2d")]
        unsafe {
            ffi::dma2d_wait()
        }
    }
}

/// Rectangle filling operation.
pub struct BitBltFill {
    bitblt: BitBlt,
}

impl BitBltFill {
    /// Prepares bitblt **fill** operation
    ///
    /// - `r` is the rectangle to fill.
    /// - `clip` is the clipping rectangle and must be completely inside the
    ///   destination bitmap.
    /// - `color` is the color to fill the rectangle with.
    /// - `alpha` is the alpha value to use for blending.
    ///
    /// The function ensures proper clipping and returns `None` if the fill
    /// operation is not needed.
    pub fn new(r: Rect, clip: Rect, color: Color, alpha: u8) -> Option<Self> {
        let r = r.clamp(clip);
        if !r.is_empty() {
            Some(Self {
                bitblt: BitBlt::default()
                    .with_rect(r)
                    .with_fg(color)
                    .with_alpha(alpha),
            })
        } else {
            None
        }
    }

    /// Fills a rectangle in the destination bitmap with the specified color.
    ///
    /// Destination bitmap must be in RGB565 format
    pub fn rgb565_fill(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGB565);
        unsafe { ffi::gl_rgb565_fill(&self.bitblt.with_dst(dst)) };
        dst.mark_dma_pending()
    }

    /// Fills a rectangle in the destination bitmap with the specified color.
    ///
    /// The destination bitmap is in the RGBA8888 format.
    pub fn rgba8888_fill(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGBA8888);
        unsafe { ffi::gl_rgba8888_fill(&self.bitblt.with_dst(dst)) };
        dst.mark_dma_pending()
    }

    /// Fills a rectangle in the destination bitmap with the specified color.
    ///
    /// The destination bitmap is in the MONO8 format.
    pub fn mono8_fill(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGBA8888);
        unsafe { ffi::gl_mono8_fill(&self.bitblt.with_dst(dst)) };
        dst.mark_dma_pending()
    }

    /// Fills a rectangle on the display with the specified color.
    #[cfg(all(not(feature = "xframebuffer"), feature = "new_rendering"))]
    pub fn display_fill(&self) {
        unsafe { ffi::display_fill(&self.bitblt) };
    }
}

/// Rectangle copying or blending operation.
pub struct BitBltCopy<'a> {
    bitblt: BitBlt,
    src: &'a BitmapView<'a>,
}

impl<'a> BitBltCopy<'a> {
    /// Prepares `BitBltCopy` structure for copying or blending a part of the source
    /// bitmap to the destination bitmap or display.
    ///
    /// - `r` is the rectangle in the destination bitmap.
    /// - `clip` is the clipping rectangle and must be completely inside the
    ///   destination bitmap.
    /// - `src` represents the source bitmap.
    ///
    /// The function ensures proper clipping and returns `None` if the copy
    /// operation is not needed.
    pub fn new(r: Rect, clip: Rect, src: &'a BitmapView) -> Option<Self> {
        let mut offset = src.offset;
        let mut r_dst = r;

        // Normalize negative x & y-offset of the bitmap
        if offset.x < 0 {
            r_dst.x0 -= offset.x;
            offset.x = 0;
        }

        if offset.y < 0 {
            r_dst.y0 -= offset.y;
            offset.y = 0;
        }

        // Clip with the canvas viewport
        let mut r = r_dst.clamp(clip);

        // Clip with the bitmap top-left
        if r.x0 > r_dst.x0 {
            offset.x += r.x0 - r_dst.x0;
        }

        if r.y0 > r_dst.y0 {
            offset.y += r.y0 - r_dst.y0;
        }

        // Clip with the bitmap size
        r.x1 = r.x1.min(r.x0 + src.size().x - offset.x);
        r.y1 = r.y1.min(r.y0 + src.size().y - offset.y);

        if !r.is_empty() {
            Some(Self {
                bitblt: BitBlt::default()
                    .with_rect(r)
                    .with_src(src.bitmap, offset.x, offset.y)
                    .with_bg(src.bg_color)
                    .with_fg(src.fg_color),
                src,
            })
        } else {
            None
        }
    }

    /// Copies a part of the source bitmap to the destination bitmap.
    ///
    /// - The source bitmap format uses MONO4.
    /// - The destination bitmap uses RGB565.
    pub fn rgb565_copy_mono4(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGB565);
        assert!(self.src.format() == BitmapFormat::MONO4);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe { ffi::gl_rgb565_copy_mono4(&self.bitblt.with_dst(dst)) };

        dst.mark_dma_pending();
        self.src.bitmap.mark_dma_pending();
    }

    /// Copies a part of the source bitmap to the destination bitmap.
    ///
    /// - The source bitmap uses the RGB565 format.
    /// - The destination bitmap usesthe RGB565 format.
    pub fn rgb565_copy_rgb565(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGB565);
        assert!(self.src.format() == BitmapFormat::RGB565);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe { ffi::gl_rgb565_copy_rgb565(&self.bitblt.with_dst(dst)) };

        dst.mark_dma_pending();
        self.src.bitmap.mark_dma_pending();
    }

    /// Blends a part of the source bitmap with the destination bitmap.
    ///
    /// - The source bitmap uses the MONO4 format.
    /// - The destination bitmap uses the RGB565 format.
    pub fn rgb565_blend_mono4(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGB565);
        assert!(self.src.format() == BitmapFormat::MONO4);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe { ffi::gl_rgb565_blend_mono4(&self.bitblt.with_dst(dst)) };

        dst.mark_dma_pending();
        self.src.bitmap.mark_dma_pending();
    }

    /// Copies a part of the source bitmap to the destination bitmap.
    ///
    /// - The source bitmap uses the MONO4 format.
    /// - The destination bitmap uses the RGBA8888 format.
    pub fn rgba8888_copy_mono4(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGBA8888);
        assert!(self.src.format() == BitmapFormat::MONO4);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe { ffi::gl_rgba8888_copy_mono4(&self.bitblt.with_dst(dst)) };

        dst.mark_dma_pending();
        self.src.bitmap.mark_dma_pending();
    }

    /// Copies a part of the source bitmap to the destination bitmap.
    ///
    /// - The source bitmap uses the RGB565 format.
    /// - The destination bitmap uses the RGBA8888 format.
    pub fn rgba8888_copy_rgb565(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGBA8888);
        assert!(self.src.format() == BitmapFormat::RGB565);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe { ffi::gl_rgba8888_copy_rgb565(&self.bitblt.with_dst(dst)) };

        dst.mark_dma_pending();
        self.src.bitmap.mark_dma_pending();
    }

    /// Copies a part of the source bitmap to the destination bitmap.
    ///
    /// - The source bitmap uses the RGBA8888 format.
    /// - The destination bitmap uses the RGBA8888 format.
    pub fn rgba8888_copy_rgba8888(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGBA8888);
        assert!(self.src.format() == BitmapFormat::RGBA8888);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe { ffi::gl_rgba8888_copy_rgba8888(&self.bitblt.with_dst(dst)) };

        dst.mark_dma_pending();
        self.src.bitmap.mark_dma_pending();
    }

    /// Blends a part of the source bitmap with the destination bitmap.
    ///
    /// - The source bitmap uses the MONO4 format.
    /// - The destination bitmap uses the RGBA8888 format.
    pub fn rgba8888_blend_mono4(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGBA8888);
        assert!(self.src.format() == BitmapFormat::MONO4);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe { ffi::gl_rgba8888_blend_mono4(&self.bitblt.with_dst(dst)) };

        dst.mark_dma_pending();
        self.src.bitmap.mark_dma_pending();
    }

    /// Copies a part of the source bitmap to the destination bitmap.
    ///
    /// - The source bitmap uses the MONO1P format.
    /// - The destination bitmap uses the MONO8 format.
    pub fn mono8_copy_mono1p(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::MONO8);
        assert!(self.src.format() == BitmapFormat::MONO1P);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe { ffi::gl_mono8_copy_mono1p(&self.bitblt.with_dst(dst)) };

        dst.mark_dma_pending();
        self.src.bitmap.mark_dma_pending();
    }

    /// Copies a part of the source bitmap to the destination bitmap.
    ///
    /// - The source bitmap uses the MONO4 format.
    /// - The destination bitmap uses the MONO8 format.
    pub fn mono8_copy_mono4(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::MONO8);
        assert!(self.src.format() == BitmapFormat::MONO4);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe { ffi::gl_mono8_copy_mono4(&self.bitblt.with_dst(dst)) };

        dst.mark_dma_pending();
        self.src.bitmap.mark_dma_pending();
    }

    /// Blends a part of the source bitmap with the destination bitmap.
    ///
    /// - The source bitmap uses the MONO1P format.
    /// - The destination bitmap uses the MONO8 format.
    pub fn mono8_blend_mono1p(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::MONO8);
        assert!(self.src.format() == BitmapFormat::MONO1P);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe { ffi::gl_mono8_blend_mono1p(&self.bitblt.with_dst(dst)) };

        dst.mark_dma_pending();
        self.src.bitmap.mark_dma_pending();
    }

    /// Blends a part of the source bitmap with the destination bitmap.
    ///
    /// - The source bitmap uses the MONO4 format.
    /// - The destination bitmap uses the MONO8 format.
    pub fn mono8_blend_mono4(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::MONO8);
        assert!(self.src.format() == BitmapFormat::MONO4);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe { ffi::gl_mono8_blend_mono4(&self.bitblt.with_dst(dst)) };

        dst.mark_dma_pending();
        self.src.bitmap.mark_dma_pending();
    }

    /// Copies a part of the source bitmap to the display.
    ///
    /// - The source bitmap uses the RGB565 format.
    #[cfg(all(not(feature = "xframebuffer"), feature = "new_rendering"))]
    pub fn display_copy_rgb565(&self) {
        assert!(self.src.format() == BitmapFormat::MONO4);

        // SAFETY:
        // - The source bitmap is in the correct formats.
        // - Source and destination coordinates are properly clipped, which is ensured
        //   by the `new()` and `with_dst()` methods.
        // - BitBlt structure is properly initialized.
        // - The DMA pending flag is set for src bitmap after operations.
        unsafe { ffi::display_copy_rgb565(&self.bitblt) };

        self.src.bitmap.mark_dma_pending();
    }
}
