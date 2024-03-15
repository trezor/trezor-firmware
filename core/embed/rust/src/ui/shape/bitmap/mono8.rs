use super::{Bitmap, BitmapFormat, BitmapView};
use crate::{
    trezorhal::dma2d_new::Dma2d,
    ui::{display::Color, geometry::Rect},
};

impl<'a> Bitmap<'a> {
    /// Fills a rectangle with the specified color.
    ///
    /// The function is aplicable only on bitmaps with RGB565 format.
    pub fn mono8_fill(&mut self, r: Rect, clip: Rect, color: Color, alpha: u8) {
        assert!(self.format() == BitmapFormat::MONO8);
        if let Some(dma2d) = Dma2d::new_fill(r, clip, color, alpha) {
            let dma2d = dma2d.with_dst(self);
            unsafe { dma2d.mono8_fill() };
            self.mark_dma_pending();
        }
    }

    //
    pub fn mono8_copy(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        assert!(self.format() == BitmapFormat::MONO8);
        if let Some(dma2d) = Dma2d::new_copy(r, clip, src) {
            let dma2d = dma2d.with_dst(self);
            match src.format() {
                BitmapFormat::MONO1P => unsafe { dma2d.mono8_copy_mono1p() },
                BitmapFormat::MONO4 => unsafe { dma2d.mono8_copy_mono4() },
                _ => panic!("Unsupported DMA operation"),
            }
            self.mark_dma_pending();
            src.bitmap.mark_dma_pending();
        }
    }

    pub fn mono8_blend(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        assert!(self.format() == BitmapFormat::MONO8);
        if let Some(dma2d) = Dma2d::new_copy(r, clip, src) {
            let dma2d = dma2d.with_dst(self);
            match src.format() {
                BitmapFormat::MONO1P => unsafe { dma2d.mono8_blend_mono1p() },
                BitmapFormat::MONO4 => unsafe { dma2d.mono8_blend_mono4() },
                _ => panic!("Unsupported DMA operation"),
            }
            self.mark_dma_pending();
            src.bitmap.mark_dma_pending();
        }
    }
}
