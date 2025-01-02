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

/// A struct representing 8-bit monochromatic canvas
pub struct Mono8Canvas<'a> {
    bitmap: Bitmap<'a>,
    viewport: Viewport,
}

impl<'a> Mono8Canvas<'a> {
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
        let bitmap = Bitmap::new_mut(BitmapFormat::MONO8, stride, size, min_height, buff)?;
        let viewport = Viewport::from_size(bitmap.size());
        Ok(Self { bitmap, viewport })
    }

    /// Returns the specified row as a mutable slice.
    ///
    /// Returns None if row is out of range.
    pub fn row_mut(&mut self, row: i16) -> Option<&mut [u8]> {
        self.bitmap.row_mut(row)
    }
}

impl<'a> BasicCanvas for Mono8Canvas<'a> {
    fn viewport(&self) -> Viewport {
        self.viewport
    }

    fn set_viewport(&mut self, viewport: Viewport) {
        self.viewport = viewport.absolute_clip(self.bounds());
    }

    fn size(&self) -> Offset {
        self.bitmap.size()
    }

    fn fill_rect(&mut self, r: Rect, color: Color, alpha: u8) {
        let r = r.translate(self.viewport.origin);
        if let Some(bitblt) = BitBltFill::new(r, self.viewport.clip, color, alpha) {
            bitblt.mono8_fill(&mut self.bitmap);
        }
    }

    fn draw_bitmap(&mut self, r: Rect, bitmap: BitmapView) {
        let r = r.translate(self.viewport.origin);
        if let Some(bitblt) = BitBltCopy::new(r, self.viewport.clip, &bitmap) {
            bitblt.mono8_copy(&mut self.bitmap);
        }
    }
}

impl<'a> CanvasBuilder<'a> for Mono8Canvas<'a> {
    fn format() -> BitmapFormat {
        BitmapFormat::MONO8
    }

    fn from_bitmap(bitmap: Bitmap<'a>) -> Self {
        assert!(bitmap.format() == Self::format());
        let viewport = Viewport::from_size(bitmap.size());
        Self { bitmap, viewport }
    }
}

impl<'a> Canvas for Mono8Canvas<'a> {
    fn view(&self) -> BitmapView {
        BitmapView::new(&self.bitmap)
    }

    fn draw_pixel(&mut self, pt: Point, color: Color) {
        let pt = pt + self.viewport.origin;
        if self.viewport.clip.contains(pt) {
            if let Some(row) = self.row_mut(pt.y) {
                row[pt.x as usize] = color.luminance() as u8;
            }
        }
    }

    fn blend_pixel(&mut self, pt: Point, color: Color, alpha: u8) {
        let pt = pt + self.viewport.origin;
        if self.viewport.clip.contains(pt) {
            if let Some(row) = self.row_mut(pt.y) {
                let pixel = &mut row[pt.x as usize];
                let fg_color = color.luminance() as u16;
                let bg_color = *pixel as u16;
                *pixel = ((fg_color * alpha as u16 + bg_color * (255 - alpha) as u16) / 255) as u8;
            }
        }
    }

    fn blend_bitmap(&mut self, r: Rect, src: BitmapView) {
        let r = r.translate(self.viewport.origin);
        if let Some(bitblt) = BitBltCopy::new(r, self.viewport.clip, &src) {
            bitblt.mono8_blend(&mut self.bitmap);
        }
    }

    #[cfg(feature = "ui_blurring")]
    fn blur_rect(&mut self, _r: Rect, _radius: usize, _cache: &DrawingCache) {
        unimplemented!();
    }
}
