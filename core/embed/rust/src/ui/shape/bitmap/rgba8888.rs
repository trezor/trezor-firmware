use super::{Bitmap, BitmapFormat, BitmapView};
use crate::{
    trezorhal::bitblt::{BitBltCopy, BitBltFill},
    ui::{display::Color, geometry::Rect},
};

impl<'a> Bitmap<'a> {
    /// Fills a rectangle with the specified color.
    ///
    /// The function is aplicable only on bitmaps with RGBA888 format.
    pub fn rgba8888_fill(&mut self, r: Rect, clip: Rect, color: Color, alpha: u8) {
        if let Some(bitblt) = BitBltFill::new(r, clip, color, alpha) {
            bitblt.rgba8888_fill(self);
        }
    }

    pub fn rgba8888_copy(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(bitblt) = BitBltCopy::new(r, clip, src) {
            match src.format() {
                BitmapFormat::MONO4 => bitblt.rgba8888_copy_mono4(self),
                BitmapFormat::RGB565 => bitblt.rgba8888_copy_rgb565(self),
                BitmapFormat::RGBA8888 => bitblt.rgba8888_copy_rgba8888(self),
                _ => panic!("Unsupported DMA operation"),
            }
        }
    }

    pub fn rgba8888_blend(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(bitblt) = BitBltCopy::new(r, clip, src) {
            match src.format() {
                BitmapFormat::MONO4 => bitblt.rgba8888_blend_mono4(self),
                _ => panic!("Unsupported DMA operation"),
            }
        }
    }
}
