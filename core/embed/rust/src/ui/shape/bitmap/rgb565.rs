use super::{Bitmap, BitmapFormat, BitmapView};
use crate::{
    trezorhal::bitblt::{BitBltCopy, BitBltFill},
    ui::{display::Color, geometry::Rect},
};

impl<'a> Bitmap<'a> {
    /// Fills a rectangle with the specified color.
    ///
    /// The function is aplicable only on bitmaps with RGB565 format.
    pub fn rgb565_fill(&mut self, r: Rect, clip: Rect, color: Color, alpha: u8) {
        if let Some(bitblt) = BitBltFill::new(r, clip, color, alpha) {
            bitblt.rgb565_fill(self);
        }
    }

    /// Copy a rectangle from the source bitmap to the destination bitmap.
    ///
    /// The function is aplicable only on bitmaps with RGB565 format.
    pub fn rgb565_copy(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(bitblt) = BitBltCopy::new(r, clip, src) {
            match src.format() {
                BitmapFormat::MONO4 => bitblt.rgb565_copy_mono4(self),
                BitmapFormat::RGB565 => bitblt.rgb565_copy_rgb565(self),
                _ => panic!("Unsupported DMA operation"),
            }
        }
    }

    /// Blend a rectangle from the source bitmap to the destination bitmap.
    ///
    /// The function is aplicable only on bitmaps with RGB565 format.
    pub fn rgb565_blend(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(bitblt) = BitBltCopy::new(r, clip, src) {
            match src.format() {
                BitmapFormat::MONO4 => bitblt.rgb565_blend_mono4(self),
                _ => panic!("Unsupported DMA operation"),
            }
        }
    }
}
