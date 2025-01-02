use super::ffi;

use crate::ui::{
    display::Color,
    geometry::Rect,
    shape::{Bitmap, BitmapFormat, BitmapView},
};

use crate::trezorhal::display::{DISPLAY_RESX, DISPLAY_RESY};

/// Waits for the DMA2D peripheral transfer to complete.
pub fn wait_for_transfer() {
    // SAFETY:
    // `ffi::gfx_bitblt_wait()` is always safe to call.
    unsafe { ffi::gfx_bitblt_wait() }
}

impl Default for ffi::gfx_bitblt_t {
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

// This is very private interface (almost completely unsafe) to
// preparing a `gfx_bitblt_t` structure for the bitblt operations.
impl ffi::gfx_bitblt_t {
    /// Sets the destination bitmap pointer and stride.
    ///
    /// # SAFETY
    /// 1) Ensure that caller holds mutable reference to the destination bitmap
    ///    until the `gfx_bitblt_t` is dropped.
    unsafe fn with_dst(self, dst: &mut Bitmap) -> Self {
        // This ensures that the destination rectangle is
        // completely inside the destination bitmap
        assert!(dst.width() as u16 >= self.dst_x + self.width);
        assert!(dst.height() as u16 >= self.dst_y + self.height);

        Self {
            // SAFETY:
            // Lines between `dst_y` and`dst_y + height` are inside
            // the destination bitmap. See asserts above.
            dst_row: unsafe { dst.row_ptr(self.dst_y) },
            dst_stride: dst.stride() as u16,
            ..self
        }
    }

    /// Sets the coordinates of the destination rectangle inside the destination
    /// bitmap.
    ///
    /// # SAFETY
    /// 1) Ensure that the rectangle is completely inside the destination
    ///    bitmap.
    /// 2) If the copy or blend operation is used, ensure that the rectangle is
    ///    completely filled with source bitmap or its part.
    unsafe fn with_rect(self, r: Rect) -> Self {
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
    /// `x` and `y` specifies offset inside the source bitmap
    ///
    /// # SAFETY
    /// 1) Ensure that `x` and `y` are inside the source bitmap.
    /// 2) Source bitmap complete covers destination rectangle.
    /// 3) Ensure that caller holds immutable reference to the source bitmap.
    ///    until the `gfx_bitblt_t` is dropped.
    unsafe fn with_src(self, bitmap: &Bitmap, x: i16, y: i16) -> Self {
        let bitmap_stride = match bitmap.format() {
            BitmapFormat::MONO1P => bitmap.width() as u16, // packed bits
            _ => bitmap.stride() as u16,
        };

        Self {
            // SAFETY:
            // It's safe if `y` is inside the bitmap (see note above)
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
}

/// Rectangle filling operation.
pub struct BitBltFill {
    bitblt: ffi::gfx_bitblt_t,
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
                // SAFETY:
                // The only unsafe operation is `.with_rect()`, which is safe
                // as long as the rectangle is completely inside the destination bitmap.
                // We will set the destination bitmap later, so at the moment the
                // rectangle cannot be out of bounds.
                bitblt: unsafe {
                    ffi::gfx_bitblt_t::default()
                        .with_rect(r)
                        .with_fg(color)
                        .with_alpha(alpha)
                },
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
        // SAFETY:
        // - The destination bitmap is in the correct format.
        // - The destination rectangle is completely inside the destination bitmap.
        unsafe { ffi::gfx_rgb565_fill(&self.bitblt.with_dst(dst)) };
        dst.mark_dma_pending();
    }

    /// Fills a rectangle in the destination bitmap with the specified color.
    ///
    /// The destination bitmap is in the RGBA8888 format.
    pub fn rgba8888_fill(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGBA8888);
        // SAFETY:
        // - The destination bitmap is in the correct format.
        // - The destination rectangle is completely inside the destination bitmap.
        unsafe { ffi::gfx_rgba8888_fill(&self.bitblt.with_dst(dst)) };
        dst.mark_dma_pending();
    }

    /// Fills a rectangle in the destination bitmap with the specified color.
    ///
    /// The destination bitmap is in the MONO8 format.
    pub fn mono8_fill(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::MONO8);
        // SAFETY:
        // - The destination bitmap is in the correct format.
        // - The destination rectangle is completely inside the destination bitmap.
        unsafe { ffi::gfx_mono8_fill(&self.bitblt.with_dst(dst)) };
        dst.mark_dma_pending();
    }

    /// Fills a rectangle on the display with the specified color.
    pub fn display_fill(&self) {
        assert!(self.bitblt.dst_x + self.bitblt.width <= DISPLAY_RESX as u16);
        assert!(self.bitblt.dst_y + self.bitblt.height <= DISPLAY_RESY as u16);
        // SAFETY:
        // - The destination rectangle is completely inside the display.
        unsafe { ffi::display_fill(&self.bitblt) };
    }
}

/// Rectangle copying or blending operation.
pub struct BitBltCopy<'a> {
    bitblt: ffi::gfx_bitblt_t,
    src: &'a BitmapView<'a>,
}

impl<'a> BitBltCopy<'a> {
    /// Prepares `BitBltCopy` structure for copying or blending a part of the
    /// source bitmap to the destination bitmap or display.
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
                // SAFETY:
                // The only unsafe operations are `.with_rect()` and `.with_src()`:
                // - There is currently no set destination so the destination rectangle can't be out
                //   of bounds
                // - The `x`, `y` offsets are within the source bitmap, as ensured by the preceding
                //   code.
                // - The source bitmap completely covers the destination rectangle, which is also
                //   ensured by the preceding code.
                // - We hold a immutable reference to the source bitmap in the `BitBltCopy`
                //   structure.
                bitblt: unsafe {
                    ffi::gfx_bitblt_t::default()
                        .with_rect(r)
                        .with_src(src.bitmap, offset.x, offset.y)
                        .with_bg(src.bg_color)
                        .with_fg(src.fg_color)
                        .with_alpha(src.alpha)
                },
                src,
            })
        } else {
            None
        }
    }

    /// Copies a part of the source bitmap to the destination bitmap in RGB565
    /// format.
    pub fn rgb565_copy(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGB565);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe {
            let bitblt = self.bitblt.with_dst(dst);
            match self.src.format() {
                BitmapFormat::MONO4 => ffi::gfx_rgb565_copy_mono4(&bitblt),
                BitmapFormat::RGB565 => ffi::gfx_rgb565_copy_rgb565(&bitblt),
                _ => unimplemented!(),
            }
        }

        self.src.bitmap.mark_dma_pending();
        dst.mark_dma_pending();
    }

    /// Blends a part of the source bitmap with the destination bitmap in RGB565
    /// format.
    pub fn rgb565_blend(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGB565);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe {
            let bitblt = self.bitblt.with_dst(dst);
            match self.src.format() {
                BitmapFormat::MONO4 => ffi::gfx_rgb565_blend_mono4(&bitblt),
                BitmapFormat::MONO8 => ffi::gfx_rgb565_blend_mono8(&bitblt),
                _ => unimplemented!(),
            }
        }

        self.src.bitmap.mark_dma_pending();
        dst.mark_dma_pending();
    }

    /// Copies a part of the source bitmap to the destination bitmap in RGBA8888
    /// format.
    pub fn rgba8888_copy(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGBA8888);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe {
            let bitblt = self.bitblt.with_dst(dst);
            match self.src.format() {
                BitmapFormat::MONO4 => ffi::gfx_rgba8888_copy_mono4(&bitblt),
                BitmapFormat::RGB565 => ffi::gfx_rgba8888_copy_rgb565(&bitblt),
                BitmapFormat::RGBA8888 => ffi::gfx_rgba8888_copy_rgba8888(&bitblt),
                _ => unimplemented!(),
            }
        }

        self.src.bitmap.mark_dma_pending();
        dst.mark_dma_pending();
    }

    /// Blends a part of the source bitmap with the destination bitmap in
    /// RGBA8888 format.
    pub fn rgba8888_blend(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::RGBA8888);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe {
            let bitblt = self.bitblt.with_dst(dst);
            match self.src.format() {
                BitmapFormat::MONO4 => ffi::gfx_rgba8888_blend_mono4(&bitblt),
                BitmapFormat::MONO8 => ffi::gfx_rgba8888_blend_mono8(&bitblt),
                _ => unimplemented!(),
            }
        }

        self.src.bitmap.mark_dma_pending();
        dst.mark_dma_pending();
    }

    /// Copies a part of the source bitmap to the destination bitmap in MONO8
    /// format.
    pub fn mono8_copy(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::MONO8);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe {
            let bitblt = self.bitblt.with_dst(dst);
            match self.src.format() {
                BitmapFormat::MONO1P => ffi::gfx_mono8_copy_mono1p(&bitblt),
                BitmapFormat::MONO4 => ffi::gfx_mono8_copy_mono4(&bitblt),
                _ => unimplemented!(),
            }
        }

        self.src.bitmap.mark_dma_pending();
        dst.mark_dma_pending();
    }

    /// Blends a part of the source bitmap with the destination bitmap in MONO8
    /// format.
    pub fn mono8_blend(&self, dst: &mut Bitmap) {
        assert!(dst.format() == BitmapFormat::MONO8);

        // SAFETY:
        // - The destination and source bitmaps are in the correct formats.
        // - Source and destination coordinates are properly clipped
        // - The DMA pending flag is set for both bitmaps after operations.
        unsafe {
            let bitblt = self.bitblt.with_dst(dst);
            match self.src.format() {
                BitmapFormat::MONO1P => ffi::gfx_mono8_blend_mono1p(&bitblt),
                BitmapFormat::MONO4 => ffi::gfx_mono8_blend_mono4(&bitblt),
                _ => unimplemented!(),
            }
        }

        self.src.bitmap.mark_dma_pending();
        dst.mark_dma_pending();
    }

    /// Copies a part of the source bitmap to the display.
    ///
    /// - The source bitmap uses the RGB565 format.
    pub fn display_copy(&self) {
        assert!(self.bitblt.dst_x + self.bitblt.width <= DISPLAY_RESX as u16);
        assert!(self.bitblt.dst_y + self.bitblt.height <= DISPLAY_RESY as u16);

        // SAFETY:
        // - The source bitmap is in the correct formats.
        // - Source and destination coordinates are properly clipped
        // - The destination rectangle is completely inside the display.
        // - The DMA pending flag is set for src bitmap after operations.
        unsafe {
            match self.src.format() {
                BitmapFormat::RGB565 => ffi::display_copy_rgb565(&self.bitblt),
                _ => unimplemented!(),
            }
        }

        self.src.bitmap.mark_dma_pending();
    }
}
