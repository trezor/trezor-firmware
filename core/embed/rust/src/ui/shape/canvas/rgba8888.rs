use crate::{
    error::Error,
    trezorhal::bitblt::{BitBltCopy, BitBltFill},
    ui::{
        display::Color,
        geometry::{Offset, Point, Rect},
    },
};

use super::{
    super::{Bitmap, BitmapFormat, BitmapView},
    BasicCanvas, Canvas, CanvasBuilder, Viewport,
};

#[cfg(feature = "ui_blurring")]
use super::super::DrawingCache;

/// A struct representing 32-bit (RGBA8888) color canvas
pub struct Rgba8888Canvas<'a> {
    bitmap: Bitmap<'a>,
    viewport: Viewport,
}

impl<'a> Rgba8888Canvas<'a> {
    /// Creates a new canvas with the specified size and buffer.
    ///
    /// Optionally minimal height can be specified and then the height
    /// of the new bitmap is adjusted to the buffer size.
    ///
    /// Returns None if the buffer is not big enough.
    pub fn new(
        size: Offset,
        stride: Option<usize>,
        min_height: Option<i16>,
        buff: &'a mut [u8],
    ) -> Result<Self, Error> {
        let bitmap = Bitmap::new_mut(BitmapFormat::RGBA8888, stride, size, min_height, buff)?;
        let viewport = Viewport::from_size(bitmap.size());
        Ok(Self { bitmap, viewport })
    }

    /// Returns the specified row as a mutable slice.
    ///
    /// Returns None if row is out of range.
    pub fn row_mut(&mut self, row: i16) -> Option<&mut [u32]> {
        self.bitmap.row_mut(row)
    }
}

impl<'a> BasicCanvas for Rgba8888Canvas<'a> {
    fn size(&self) -> Offset {
        self.bitmap.size()
    }

    fn viewport(&self) -> Viewport {
        self.viewport
    }

    fn set_viewport(&mut self, viewport: Viewport) {
        self.viewport = viewport.absolute_clip(self.bounds());
    }

    fn fill_rect(&mut self, r: Rect, color: Color, alpha: u8) {
        let r = r.translate(self.viewport.origin);
        if let Some(bitblt) = BitBltFill::new(r, self.viewport.clip, color, alpha) {
            bitblt.rgba8888_fill(&mut self.bitmap);
        }
    }

    fn draw_bitmap(&mut self, r: Rect, bitmap: BitmapView) {
        let r = r.translate(self.viewport.origin);
        if let Some(bitblt) = BitBltCopy::new(r, self.viewport.clip, &bitmap) {
            bitblt.rgba8888_copy(&mut self.bitmap);
        }
    }
}

impl<'a> CanvasBuilder<'a> for Rgba8888Canvas<'a> {
    fn format() -> BitmapFormat {
        BitmapFormat::RGBA8888
    }

    fn from_bitmap(bitmap: Bitmap<'a>) -> Self {
        assert!(bitmap.format() == Self::format());
        let viewport = Viewport::from_size(bitmap.size());
        Self { bitmap, viewport }
    }
}

impl<'a> Canvas for Rgba8888Canvas<'a> {
    fn view(&self) -> BitmapView {
        BitmapView::new(&self.bitmap)
    }

    fn draw_pixel(&mut self, pt: Point, color: Color) {
        let pt = pt + self.viewport.origin;
        if self.viewport.clip.contains(pt) {
            if let Some(row) = self.row_mut(pt.y) {
                row[pt.x as usize] = color.to_u32();
            }
        }
    }

    fn blend_pixel(&mut self, pt: Point, color: Color, alpha: u8) {
        let pt = pt + self.viewport.origin;
        if self.viewport.clip.contains(pt) {
            if let Some(row) = self.row_mut(pt.y) {
                let bg = row[pt.x as usize];

                let bg_r = ((bg & 0x00FF0000) >> 16) as u16;
                let bg_g = ((bg & 0x0000FF00) >> 8) as u16;
                let bg_b = (bg & 0x000000FF) as u16;

                let fg_r = color.r() as u16;
                let fg_g = color.g() as u16;
                let fg_b = color.b() as u16;

                let fg_mul = alpha as u16;
                let bg_mul = (255 - alpha) as u16;

                let r = ((fg_r * fg_mul + bg_r * bg_mul) / 255) as u32;
                let g = ((fg_g * fg_mul + bg_g * bg_mul) / 255) as u32;
                let b = ((fg_b * fg_mul + bg_b * bg_mul) / 255) as u32;

                row[pt.x as usize] = (0xFF << 24) | (r << 16) | (g << 8) | b;
            }
        }
    }

    fn blend_bitmap(&mut self, r: Rect, src: BitmapView) {
        let r = r.translate(self.viewport.origin);
        if let Some(bitblt) = BitBltCopy::new(r, self.viewport.clip, &src) {
            bitblt.rgba8888_blend(&mut self.bitmap);
        }
    }

    #[cfg(feature = "ui_blurring")]
    fn blur_rect(&mut self, _r: Rect, _radius: usize, _cache: &DrawingCache) {
        // TODO
    }
}
