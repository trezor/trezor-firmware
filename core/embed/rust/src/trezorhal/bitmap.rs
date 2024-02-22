use super::ffi;

use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
};

use core::{cell::Cell, marker::PhantomData};

#[derive(Copy, Clone)]
pub enum BitmapFormat {
    MONO1,
    MONO1P,
    MONO4,
    MONO8,
    RGB565,
    RGBA8888,
}

pub struct Bitmap<'a> {
    /// Pointer to top-left pixel
    ptr: *mut u8,
    /// Stride in bytes
    stride: usize,
    /// Size in pixels
    size: Offset,
    /// Format of pixels
    format: BitmapFormat,
    /// Bitmap data is mutable
    mutable: bool,
    /// DMA operation is pending
    dma_pending: Cell<bool>,
    ///
    _phantom: core::marker::PhantomData<&'a ()>,
}

impl<'a> Bitmap<'a> {
    /// Creates a new bitmap referencing a specified buffer.
    ///
    /// Optionally minimal height can be specified and then the height
    /// of the new bitmap is adjusted to the buffer size.
    ///
    /// Returns None if the buffer is not big enough.
    ///
    /// The `buff` needs to be properly aligned and big enough
    /// to hold a bitmap with the specified format and size
    pub fn new(
        format: BitmapFormat,
        stride: Option<usize>,
        mut size: Offset,
        min_height: Option<i16>,
        buff: &'a [u8],
    ) -> Option<Self> {
        if size.x < 0 && size.y < 0 {
            return None;
        }

        let min_stride = match format {
            BitmapFormat::MONO1 => (size.x + 7) / 8,
            BitmapFormat::MONO1P => 0,
            BitmapFormat::MONO4 => (size.x + 1) / 2,
            BitmapFormat::MONO8 => size.x,
            BitmapFormat::RGB565 => size.x * 2,
            BitmapFormat::RGBA8888 => size.x * 4,
        } as usize;

        let stride = stride.unwrap_or(min_stride);

        let alignment = match format {
            BitmapFormat::MONO1 => 1,
            BitmapFormat::MONO1P => 1,
            BitmapFormat::MONO4 => 1,
            BitmapFormat::MONO8 => 1,
            BitmapFormat::RGB565 => 2,
            BitmapFormat::RGBA8888 => 4,
        };

        assert!(stride >= min_stride);
        assert!(buff.as_ptr() as usize & (alignment - 1) == 0);
        assert!(stride & (alignment - 1) == 0);

        let max_height = if stride == 0 {
            size.y as usize
        } else {
            buff.len() / stride
        };

        if size.y as usize > max_height {
            if let Some(min_height) = min_height {
                if max_height >= min_height as usize {
                    size.y = max_height as i16;
                } else {
                    return None;
                }
            } else {
                return None;
            }
        }

        Some(Self {
            ptr: buff.as_ptr() as *mut u8,
            stride,
            size,
            format,
            mutable: false,
            dma_pending: Cell::new(false),
            _phantom: PhantomData,
        })
    }

    /// Creates a new mutable bitmap referencing a specified buffer.
    ///
    /// Optionally minimal height can be specified and then the height
    /// of the new bitmap is adjusted to the buffer size.
    ///
    /// Returns None if the buffer is not big enough.
    ///
    /// The `buff` needs to be properly aligned and big enough
    /// to hold a bitmap with the specified format and size
    pub fn new_mut(
        format: BitmapFormat,
        stride: Option<usize>,
        size: Offset,
        min_height: Option<i16>,
        buff: &'a mut [u8],
    ) -> Option<Self> {
        let mut bitmap = Self::new(format, stride, size, min_height, buff)?;
        bitmap.mutable = true;
        return Some(bitmap);
    }

    /// Returns bitmap width in pixels.
    pub fn width(&self) -> i16 {
        self.size.x
    }

    /// Returns bitmap height in pixels.
    pub fn height(&self) -> i16 {
        self.size.y
    }

    /// Returns bitmap width and height in pixels.
    pub fn size(&self) -> Offset {
        self.size
    }

    /// Returns bitmap stride in bytes.
    pub fn stride(&self) -> usize {
        self.stride
    }

    pub fn view(&self) -> BitmapView {
        BitmapView::new(&self)
    }

    /// Returns the specified row as an immutable slice.
    ///
    /// Returns None if row is out of range.
    pub fn row<T>(&self, row: i16) -> Option<&[T]> {
        if row >= 0 && row < self.size.y {
            self.wait_for_dma();
            let offset = row as usize * (self.stride / core::mem::size_of::<T>());
            Some(unsafe {
                core::slice::from_raw_parts(
                    (self.ptr as *const T).add(offset),
                    self.stride / core::mem::size_of::<T>(),
                )
            })
        } else {
            None
        }
    }

    /// Returns the specified row as a mutable slice.
    ///
    /// Returns None if row is out of range.
    pub fn row_mut<T>(&mut self, row: i16) -> Option<&mut [T]> {
        if row >= 0 && row < self.size.y {
            self.wait_for_dma();
            let offset = row as usize * (self.stride / core::mem::size_of::<T>());
            Some(unsafe {
                core::slice::from_raw_parts_mut(
                    (self.ptr as *mut T).add(offset),
                    self.stride / core::mem::size_of::<T>(),
                )
            })
        } else {
            None
        }
    }

    /// Returns specified consecutive rows as a mutable slice
    ///
    /// Returns None if any of requested row is out of range.
    pub fn rows_mut<T>(&mut self, row: i16, height: i16) -> Option<&mut [T]> {
        if row >= 0 && height > 0 && row < self.size.y && row + height <= self.size.y {
            self.wait_for_dma();
            let offset = self.stride * row as usize;
            let len = self.stride * height as usize;

            let array = unsafe {
                core::slice::from_raw_parts_mut(
                    self.ptr as *mut T,
                    self.size.y as usize * self.stride / core::mem::size_of::<T>(),
                )
            };

            Some(&mut array[offset..offset + len])
        } else {
            None
        }
    }

    /// Fills a rectangle with the specified color.
    ///
    /// The function is aplicable only on bitmaps with RGB565 format.
    pub fn rgb565_fill(&mut self, r: Rect, clip: Rect, color: Color, alpha: u8) {
        if let Some(dma2d) = Dma2d::new_fill(r, clip, color, alpha) {
            let dma2d = dma2d.with_dst(self);
            unsafe {
                ffi::rgb565_fill(&dma2d);
            }
            self.dma_pending.set(true);
        }
    }

    //
    pub fn rgb565_copy(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(dma2d) = Dma2d::new_copy(r, clip, src) {
            let dma2d = dma2d.with_dst(self);
            unsafe {
                match src.bitmap.format {
                    BitmapFormat::MONO4 => {
                        ffi::rgb565_copy_mono4(&dma2d);
                    }
                    BitmapFormat::RGB565 => {
                        ffi::rgb565_copy_rgb565(&dma2d);
                    }
                    _ => panic!(),
                }
            }
            self.dma_pending.set(true);
            src.bitmap.dma_pending.set(true);
        }
    }

    pub fn rgb565_blend(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(dma2d) = Dma2d::new_copy(r, clip, src) {
            let dma2d = dma2d.with_dst(self);
            unsafe {
                match src.bitmap.format {
                    BitmapFormat::MONO1P => {
                        // TODO
                    }
                    BitmapFormat::MONO4 => {
                        ffi::rgb565_blend_mono4(&dma2d);
                    }
                    _ => panic!(),
                }
            }
            self.dma_pending.set(true);
            src.bitmap.dma_pending.set(true);
        }
    }

    /// Fills a rectangle with the specified color.
    ///
    /// The function is aplicable only on bitmaps with RGBA888 format.
    pub fn rgba8888_fill(&mut self, r: Rect, clip: Rect, color: Color, alpha: u8) {
        if let Some(dma2d) = Dma2d::new_fill(r, clip, color, alpha) {
            let dma2d = dma2d.with_dst(self);
            unsafe {
                ffi::rgba8888_fill(&dma2d);
            }
            self.dma_pending.set(true);
        }
    }

    pub fn rgba8888_copy(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(dma2d) = Dma2d::new_copy(r, clip, src) {
            let dma2d = dma2d.with_dst(self);
            unsafe {
                match src.bitmap.format {
                    BitmapFormat::MONO4 => {
                        ffi::rgba8888_copy_mono4(&dma2d);
                    }
                    BitmapFormat::RGB565 => {
                        ffi::rgba8888_copy_rgb565(&dma2d);
                    }
                    BitmapFormat::RGBA8888 => {
                        ffi::rgba8888_copy_rgba8888(&dma2d);
                    }
                    _ => panic!(),
                }
            }
            self.dma_pending.set(true);
            src.bitmap.dma_pending.set(true);
        }
    }

    pub fn rgba8888_blend(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(dma2d) = Dma2d::new_copy(r, clip, src) {
            let dma2d = dma2d.with_dst(self);
            unsafe {
                match src.bitmap.format {
                    BitmapFormat::MONO4 => {
                        ffi::rgba8888_blend_mono4(&dma2d);
                    }
                    _ => panic!(),
                }
            }
            self.dma_pending.set(true);
            src.bitmap.dma_pending.set(true);
        }
    }

    /// Fills a rectangle with the specified color.
    ///
    /// The function is aplicable only on bitmaps with RGB565 format.
    pub fn mono8_fill(&mut self, r: Rect, clip: Rect, color: Color, alpha: u8) {
        if let Some(dma2d) = Dma2d::new_fill(r, clip, color, alpha) {
            let dma2d = dma2d.with_dst(self);
            unsafe {
                ffi::mono8_fill(&dma2d);
            }
            self.dma_pending.set(true);
        }
    }

    //
    pub fn mono8_copy(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(dma2d) = Dma2d::new_copy(r, clip, src) {
            let dma2d = dma2d.with_dst(self);
            unsafe {
                match src.bitmap.format {
                    BitmapFormat::MONO1P => {
                        ffi::mono8_copy_mono1p(&dma2d);
                    }
                    BitmapFormat::MONO4 => {
                        ffi::mono8_copy_mono4(&dma2d);
                    }
                    _ => panic!(),
                }
            }
            self.dma_pending.set(true);
            src.bitmap.dma_pending.set(true);
        }
    }

    pub fn mono8_blend(&mut self, r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(dma2d) = Dma2d::new_copy(r, clip, src) {
            let dma2d = dma2d.with_dst(self);
            unsafe {
                match src.bitmap.format {
                    BitmapFormat::MONO1P => {
                        ffi::mono8_blend_mono1p(&dma2d);
                    }
                    BitmapFormat::MONO4 => {
                        ffi::mono8_blend_mono4(&dma2d);
                    }
                    _ => panic!(),
                }
            }
            self.dma_pending.set(true);
            src.bitmap.dma_pending.set(true);
        }
    }

    /// Waits until DMA operation is finished
    fn wait_for_dma(&self) {
        if self.dma_pending.get() {
            #[cfg(feature = "dma2d")]
            unsafe {
                ffi::dma2d_wait_for_transfer();
            }
            self.dma_pending.set(false);
        }
    }
}

impl<'a> Drop for Bitmap<'a> {
    fn drop(&mut self) {
        self.wait_for_dma();
    }
}

pub struct BitmapView<'a> {
    pub bitmap: &'a Bitmap<'a>,
    pub offset: Offset,
    pub fg_color: Color,
    pub bg_color: Color,
}

impl<'a> BitmapView<'a> {
    /// Creates a new reference to the bitmap
    pub fn new(bitmap: &'a Bitmap) -> Self {
        Self {
            bitmap,
            offset: Offset::zero(),
            fg_color: Color::black(),
            bg_color: Color::black(),
        }
    }

    /// Builds a new structure with offset set to the specified value
    pub fn with_offset(self, offset: Offset) -> Self {
        Self {
            offset: (offset + self.offset.into()).into(),
            ..self
        }
    }

    /// Builds a new structure with foreground color set to the specified value
    pub fn with_fg(self, fg_color: Color) -> Self {
        Self {
            fg_color: fg_color.into(),
            ..self
        }
    }

    /// Builds a new structure with background color set to the specified value
    pub fn with_bg(self, bg_color: Color) -> Self {
        Self {
            bg_color: bg_color.into(),
            ..self
        }
    }

    /// Returns the bitmap width and height in pixels
    pub fn size(&self) -> Offset {
        self.bitmap.size
    }

    /// Returns the bitmap width in pixels
    pub fn width(&self) -> i16 {
        self.bitmap.width()
    }

    /// Returns the bitmap height in pixels
    pub fn height(&self) -> i16 {
        self.bitmap.height()
    }

    /// Returns the bitmap format
    pub fn format(&self) -> BitmapFormat {
        self.bitmap.format
    }

    /// Returns the specified row as an immutable slice.
    ///
    /// Returns None if row is out of range.
    pub fn row<T>(&self, row: i16) -> Option<&[T]> {
        self.bitmap.row(row)
    }
}

pub type Dma2d = ffi::dma2d_params_t;

impl Dma2d {
    pub fn new_fill(r: Rect, clip: Rect, color: Color, alpha: u8) -> Option<Self> {
        let r = r.intersect(clip);
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
        let mut r = r_dst.intersect(clip);

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
            dst_row: unsafe { dst.ptr.add(dst.stride * self.dst_y as usize) as *mut cty::c_void },
            dst_stride: dst.stride as u16,
            ..self
        }
    }

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
        let bitmap_stride = match bitmap.format {
            BitmapFormat::MONO1P => bitmap.size.x as u16, // packed bits
            _ => bitmap.stride as u16,
        };

        Self {
            src_row: unsafe { bitmap.ptr.add(bitmap.stride * y as usize) as *mut cty::c_void },
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
}

impl Dma2d {
    pub fn wnd565_fill(r: Rect, clip: Rect, color: Color) {
        if let Some(dma2d) = Dma2d::new_fill(r, clip, color, 255) {
            unsafe { ffi::wnd565_fill(&dma2d) };
        }
    }

    pub fn wnd565_copy(r: Rect, clip: Rect, src: &BitmapView) {
        if let Some(dma2d) = Dma2d::new_copy(r, clip, src) {
            unsafe {
                match src.bitmap.format {
                    BitmapFormat::RGB565 => {
                        ffi::wnd565_copy_rgb565(&dma2d);
                    }
                    _ => panic!(),
                }
            }
            src.bitmap.dma_pending.set(true);
        }
    }
}
