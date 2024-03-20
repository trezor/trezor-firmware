use super::ffi;

use crate::ui::{
    display::Color,
    geometry::Rect,
    shape::{Bitmap, BitmapFormat, BitmapView},
};

pub type Dma2d = ffi::dma2d_params_t;

impl Default for Dma2d {
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

impl Dma2d {
    pub fn new_fill(r: Rect, clip: Rect, color: Color, alpha: u8) -> Option<Self> {
        let r = r.clamp(clip);
        if !r.is_empty() {
            Some(
                Self::default()
                    .with_rect(r)
                    .with_fg(color)
                    .with_alpha(alpha),
            )
        } else {
            None
        }
    }

    pub fn new_copy(r: Rect, clip: Rect, src: &BitmapView) -> Option<Self> {
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
        r.x1 = core::cmp::min(r.x0 + src.size().x - offset.x, r.x1);
        r.y1 = core::cmp::min(r.y0 + src.size().y - offset.y, r.y1);

        if !r.is_empty() {
            Some(
                Dma2d::default()
                    .with_rect(r)
                    .with_src(src.bitmap, offset.x, offset.y)
                    .with_bg(src.bg_color)
                    .with_fg(src.fg_color),
            )
        } else {
            None
        }
    }

    pub fn with_dst(self, dst: &mut Bitmap) -> Self {
        Self {
            dst_row: unsafe { dst.row_ptr(self.dst_y) },
            dst_stride: dst.stride() as u16,
            ..self
        }
    }

    fn with_rect(self, r: Rect) -> Self {
        Self {
            width: r.width() as u16,
            height: r.height() as u16,
            dst_x: r.x0 as u16,
            dst_y: r.y0 as u16,
            ..self
        }
    }

    fn with_src(self, bitmap: &Bitmap, x: i16, y: i16) -> Self {
        let bitmap_stride = match bitmap.format() {
            BitmapFormat::MONO1P => bitmap.width() as u16, // packed bits
            _ => bitmap.stride() as u16,
        };

        Self {
            src_row: unsafe { bitmap.row_ptr(y as u16) },
            src_stride: bitmap_stride,
            src_x: x as u16,
            src_y: y as u16,
            ..self
        }
    }

    fn with_fg(self, fg_color: Color) -> Self {
        Self {
            src_fg: fg_color.into(),
            ..self
        }
    }

    fn with_bg(self, bg_color: Color) -> Self {
        Self {
            src_bg: bg_color.into(),
            ..self
        }
    }

    fn with_alpha(self, alpha: u8) -> Self {
        Self {
            src_alpha: alpha,
            ..self
        }
    }

    pub fn wait_for_transfer() {
        unsafe { ffi::dma2d_wait_for_transfer() }
    }

    pub unsafe fn rgb565_fill(&self) {
        unsafe { ffi::rgb565_fill(self) };
    }

    pub unsafe fn rgb565_copy_mono4(&self) {
        unsafe { ffi::rgb565_copy_mono4(self) };
    }

    pub unsafe fn rgb565_copy_rgb565(&self) {
        unsafe { ffi::rgb565_copy_rgb565(self) };
    }

    pub unsafe fn rgb565_blend_mono4(&self) {
        unsafe { ffi::rgb565_blend_mono4(self) };
    }

    pub unsafe fn rgba8888_fill(&self) {
        unsafe { ffi::rgba8888_fill(self) };
    }

    pub unsafe fn rgba8888_copy_mono4(&self) {
        unsafe { ffi::rgba8888_copy_mono4(self) };
    }

    pub unsafe fn rgba8888_copy_rgb565(&self) {
        unsafe { ffi::rgba8888_copy_rgb565(self) };
    }

    pub unsafe fn rgba8888_copy_rgba8888(&self) {
        unsafe { ffi::rgba8888_copy_rgba8888(self) };
    }

    pub unsafe fn rgba8888_blend_mono4(&self) {
        unsafe { ffi::rgba8888_blend_mono4(self) };
    }

    pub unsafe fn mono8_fill(&self) {
        unsafe { ffi::mono8_fill(self) };
    }

    pub unsafe fn mono8_copy_mono1p(&self) {
        unsafe { ffi::mono8_copy_mono1p(self) };
    }

    pub unsafe fn mono8_copy_mono4(&self) {
        unsafe { ffi::mono8_copy_mono4(self) };
    }

    pub unsafe fn mono8_blend_mono1p(&self) {
        unsafe { ffi::mono8_blend_mono1p(self) };
    }

    pub unsafe fn mono8_blend_mono4(&self) {
        unsafe { ffi::mono8_blend_mono4(self) };
    }

    pub unsafe fn wnd565_fill(&self) {
        unsafe { ffi::wnd565_fill(self) };
    }

    pub unsafe fn wnd565_copy_rgb565(&self) {
        unsafe { ffi::wnd565_copy_rgb565(self) };
    }
}
