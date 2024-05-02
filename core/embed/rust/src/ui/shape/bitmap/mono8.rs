use super::{Bitmap, BitmapFormat, BitmapView};
use crate::{
    trezorhal::bitblt::{BitBltCopy, BitBltFill},
    ui::{display::Color, geometry::Rect},
};

impl<'a> Bitmap<'a> {
    /// Fills a rectangle with the specified color.
    ///
    /// The function is aplicable only on bitmaps with MONO8 format.
    pub fn mono8_fill(&mut self, r: Rect, clip: Rect, color: Color, alpha: u8) {
        if let Some(bitblt) = BitBltFill::new(r, clip, color, alpha) {
            bitblt.mono8_fill(self);
        }
    }

    //
    pub fn mono8_copy(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(bitblt) = BitBltCopy::new(r, clip, src) {
            match src.format() {
                BitmapFormat::MONO1P => bitblt.mono8_copy_mono1p(self),
                BitmapFormat::MONO4 => bitblt.mono8_copy_mono4(self),
                _ => panic!("Unsupported DMA operation"),
            }
        }
    }

    pub fn mono8_blend(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(bitblt) = BitBltCopy::new(r, clip, src) {
            match src.format() {
                BitmapFormat::MONO1P => bitblt.mono8_blend_mono1p(self),
                BitmapFormat::MONO4 => bitblt.mono8_blend_mono4(self),
                _ => panic!("Unsupported DMA operation"),
            }
        }
    }
}
