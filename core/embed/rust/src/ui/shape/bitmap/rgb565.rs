use super::{Bitmap, BitmapFormat, BitmapView};
use crate::{
    trezorhal::bitblt::BitBlt,
    ui::{display::Color, geometry::Rect},
};

impl<'a> Bitmap<'a> {
    /// Fills a rectangle with the specified color.
    ///
    /// The function is aplicable only on bitmaps with RGB565 format.
    pub fn rgb565_fill(&mut self, r: Rect, clip: Rect, color: Color, alpha: u8) {
        assert!(self.format() == BitmapFormat::RGB565);
        if let Some(bitblt) = BitBlt::new_fill(r, clip, color, alpha) {
            let bitblt = bitblt.with_dst(self);
            unsafe { bitblt.rgb565_fill() };
            self.mark_dma_pending();
        }
    }

    //
    pub fn rgb565_copy(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        assert!(self.format() == BitmapFormat::RGB565);
        if let Some(bitblt) = BitBlt::new_copy(r, clip, src) {
            let bitblt = bitblt.with_dst(self);
            match src.format() {
                BitmapFormat::MONO4 => unsafe { bitblt.rgb565_copy_mono4() },
                BitmapFormat::RGB565 => unsafe { bitblt.rgb565_copy_rgb565() },
                _ => panic!("Unsupported DMA operation"),
            }
            self.mark_dma_pending();
            src.bitmap.mark_dma_pending();
        }
    }

    pub fn rgb565_blend(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        assert!(self.format() == BitmapFormat::RGB565);
        if let Some(bitblt) = BitBlt::new_copy(r, clip, src) {
            let bitblt = bitblt.with_dst(self);
            match src.format() {
                BitmapFormat::MONO4 => unsafe { bitblt.rgb565_blend_mono4() },
                _ => panic!("Unsupported DMA operation"),
            }
            self.mark_dma_pending();
            src.bitmap.mark_dma_pending();
        }
    }
}
