use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
};

use qrcodegen::QrCode;

use super::{
    utils::line_points, Bitmap, BitmapFormat, Canvas, DrawingCache, Renderer, Shape, ShapeClone,
};

use without_alloc::alloc::LocalAllocLeakExt;

const MAX_QRCODE_BYTES: usize = 400;

/// A shape for `QrCode` rendering.
pub struct QrImage {
    /// Destination rectangle
    area: Rect,
    /// QR code bitmap
    qr_modules: [u8; MAX_QRCODE_BYTES],
    /// Size of QR code bitmap in bytes
    qr_size: i16,
    /// Foreground color
    fg_color: Color,
    /// Optional background color
    bg_color: Option<Color>,
}

impl QrImage {
    pub fn new(area: Rect, qrcode: &QrCode) -> Self {
        if area.width() < qrcode.size() as i16 || area.height() < qrcode.size() as i16 {
            fatal_error!("Too small area");
        }

        let mut result = QrImage {
            area,
            qr_size: qrcode.size() as i16,
            qr_modules: [0u8; MAX_QRCODE_BYTES],
            fg_color: Color::white(),
            bg_color: None,
        };

        // Copy content of QR code to the qrmodules buffer
        for y in 0..result.qr_size {
            for x in 0..result.qr_size {
                result.set_module(x, y, qrcode.get_module(x as i32, y as i32));
            }
        }

        result
    }

    fn set_module(&mut self, x: i16, y: i16, value: bool) {
        // Every row starts at byte aligned address
        let row_offset = (y * (self.qr_size + 7) / 8) as usize;
        let row = &mut self.qr_modules[row_offset..];
        let col_offset = (x / 8) as usize;
        let col_bit = 1 << (x & 0x7);
        if value {
            row[col_offset] |= col_bit;
        } else {
            row[col_offset] &= col_bit ^ 0xFF;
        }
    }

    fn get_module(&self, x: i16, y: i16) -> bool {
        // Every row starts at byte aligned address
        let row_offset = (y * (self.qr_size + 7) / 8) as usize;
        let row = &self.qr_modules[row_offset..];
        let col_offset = (x / 8) as usize;
        let col_bit = 1 << (x & 0x7);
        (row[col_offset] & col_bit) != 0
    }

    pub fn with_fg(self, fg_color: Color) -> Self {
        Self { fg_color, ..self }
    }

    pub fn with_bg(self, bg_color: Color) -> Self {
        Self {
            bg_color: Some(bg_color),
            ..self
        }
    }

    pub fn render<'s>(self, renderer: &mut impl Renderer<'s>) {
        renderer.render_shape(self);
    }

    fn draw_row(&self, slice_row: &mut [u8], qr_y: i16) {
        slice_row.iter_mut().for_each(|b| *b = 0);

        let mut qr_module = false;

        for p in line_points(self.area.x1 - self.area.x0, self.qr_size, 0) {
            if p.first {
                qr_module = self.get_module(p.v, qr_y);
            }
            if !qr_module {
                if p.u & 0x01 == 0 {
                    slice_row[(p.u / 2) as usize] |= 0x0F;
                } else {
                    slice_row[(p.u / 2) as usize] |= 0xF0;
                }
            }
        }
    }
}

impl Shape<'_> for QrImage {
    fn bounds(&self) -> Rect {
        self.area
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {}

    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache) {
        let buff = &mut unwrap!(cache.image_buff(), "No TOIF buffer");

        let mut slice = unwrap!(
            Bitmap::new_mut(
                BitmapFormat::MONO4,
                None,
                Offset::new(self.area.width(), 1),
                None,
                &mut buff[..]
            ),
            "Too small buffer"
        );

        let clip = canvas.viewport().relative_clip(self.bounds()).clip;

        // translate clip to the relative coordinates
        let clip = clip.translate(-canvas.viewport().origin);
        let clip = clip.translate((-self.area.top_left()).into());

        for p in line_points(self.area.y1 - self.area.y0, self.qr_size, clip.y0)
            .take(clip.height() as usize)
        {
            if p.first {
                self.draw_row(slice.row_mut(0).unwrap(), p.v);
            }

            let r = Rect {
                y0: self.area.y0 + p.u,
                y1: self.area.y0 + p.u + 1,
                ..self.area
            };

            let slice_view = slice.view().with_fg(self.fg_color);

            match self.bg_color {
                Some(bg_color) => canvas.draw_bitmap(r, slice_view.with_bg(bg_color)),
                None => canvas.blend_bitmap(r, slice_view),
            }
        }
    }
}

impl<'s> ShapeClone<'s> for QrImage {
    fn clone_at_bump<T>(self, bump: &'s T) -> Option<&'s mut dyn Shape<'s>>
    where
        T: LocalAllocLeakExt<'s>,
    {
        let clone = bump.alloc_t()?;
        Some(clone.uninit.init(QrImage { ..self }))
    }
}
