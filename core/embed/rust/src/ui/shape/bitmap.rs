use crate::{error::Error, trezorhal::bitblt};

use crate::ui::{display::Color, geometry::Offset};

use core::{cell::Cell, marker::PhantomData};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum BitmapFormat {
    /// 1-bit mono
    MONO1,
    /// 1-bit mono packed (bitmap stride is in bits)
    MONO1P,
    /// 4-bit mono
    MONO4,
    /// 8-bit mono
    MONO8,
    /// 16-bit color, RGB565 format
    RGB565,
    /// 32-bit color, RGBA format
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
    /// DMA operation is pending.
    ///
    /// If this flag is set, a DMA operation on the pointed-to buffer
    /// may be pending and so nobody is allowed to look at it --
    /// either through a pre-existing reference (so the Bitmap object must not
    /// be dropped) or through one of Bitmap's methods.
    ///
    /// The `Bitmap` ensures that by `wait_for_dma()`ing the buffer before
    /// dropping it or doing anything else with it.
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
    ) -> Result<Self, Error> {
        assert!(size.x >= 0 && size.y >= 0);

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
        assert!(buff.as_ptr().align_offset(alignment) == 0);
        assert!(stride % alignment == 0);

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
                    return Err(Error::ValueError(c"Buffer too small."));
                }
            } else {
                return Err(Error::ValueError(c"Buffer too small."));
            }
        }

        Ok(Self {
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
    ) -> Result<Self, Error> {
        let mut bitmap = Self::new(format, stride, size, min_height, buff)?;
        bitmap.mutable = true;
        Ok(bitmap)
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

    /// Returns bitmap format.
    pub fn format(&self) -> BitmapFormat {
        self.format
    }

    pub fn view(&self) -> BitmapView {
        BitmapView::new(self)
    }

    /// Returns the specified row as an immutable slice.
    ///
    /// Returns None if row is out of range.
    pub fn row<T>(&self, row: i16) -> Option<&[T]> {
        if row < 0 || row >= self.size.y {
            return None;
        }

        let offset = row as usize * (self.stride / core::mem::size_of::<T>());

        if offset % core::mem::align_of::<T>() != 0 {
            return None;
        }

        self.wait_for_dma();

        // SAFETY:
        // The resulting slice is inside the bitmap and properly aligned.
        // Potential DMA operation is finished.
        Some(unsafe {
            core::slice::from_raw_parts(
                (self.ptr as *const T).add(offset),
                self.stride / core::mem::size_of::<T>(),
            )
        })
    }

    /// Returns the specified row as a mutable slice.
    ///
    /// Returns None if row is out of range or
    /// the bitmap is not set as mutable.
    pub fn row_mut<T>(&mut self, row: i16) -> Option<&mut [T]> {
        if !self.mutable {
            return None;
        }

        if row < 0 || row >= self.size.y {
            return None;
        }

        let offset = row as usize * (self.stride / core::mem::size_of::<T>());

        if offset % core::mem::align_of::<T>() != 0 {
            return None;
        }

        self.wait_for_dma();

        // SAFETY:
        // The bitmap is mutable.
        // The resulting slice is inside the bitmap and properly aligned.
        // Potential DMA operation is finished.
        Some(unsafe {
            core::slice::from_raw_parts_mut(
                (self.ptr as *mut T).add(offset),
                self.stride / core::mem::size_of::<T>(),
            )
        })
    }

    /// Returns specified consecutive rows as a mutable slice
    ///
    /// Returns None if any of requested row is out of range or
    /// the bitmap is not set as mutable.
    pub fn rows_mut<T>(&mut self, row: i16, height: i16) -> Option<&mut [T]> {
        if !self.mutable {
            return None;
        }

        if row < 0 || height <= 0 || row + height > self.size.y {
            return None;
        }

        let offset = self.stride * row as usize;

        if offset % core::mem::align_of::<T>() != 0 {
            return None;
        }

        self.wait_for_dma();

        // SAFETY:
        // The bitmap is mutable.
        // The resulting slice is inside the bitmap and properly aligned.
        // Potential DMA operation is finished.
        let array = unsafe {
            core::slice::from_raw_parts_mut(
                self.ptr as *mut T,
                self.size.y as usize * self.stride / core::mem::size_of::<T>(),
            )
        };

        let len = self.stride * height as usize;

        Some(&mut array[offset..offset + len])
    }

    /// Return raw mut pointer to the specified bitmap row.
    ///
    /// # Safety
    ///
    /// `y` must be in range <0; self.height() - 1>.
    pub unsafe fn row_ptr(&self, y: u16) -> *mut cty::c_void {
        unsafe { self.ptr.add(self.stride() * y as usize) as *mut cty::c_void }
    }

    /// Waits until DMA operation is finished
    fn wait_for_dma(&self) {
        if self.dma_pending.get() {
            bitblt::wait_for_transfer();
            self.dma_pending.set(false);
        }
    }

    // Mark bitmap as DMA operation is pending
    pub fn mark_dma_pending(&self) {
        self.dma_pending.set(true);
    }
}

impl<'a> Drop for Bitmap<'a> {
    fn drop(&mut self) {
        self.wait_for_dma();
    }
}

#[derive(Copy, Clone)]
pub struct BitmapView<'a> {
    pub bitmap: &'a Bitmap<'a>,
    pub offset: Offset,
    pub fg_color: Color,
    pub bg_color: Color,
    pub alpha: u8,
}

impl<'a> BitmapView<'a> {
    /// Creates a new reference to the bitmap
    pub fn new(bitmap: &'a Bitmap) -> Self {
        Self {
            bitmap,
            offset: Offset::zero(),
            fg_color: Color::black(),
            bg_color: Color::black(),
            alpha: 255,
        }
    }

    /// Builds a new structure with offset set to the specified value
    pub fn with_offset(self, offset: Offset) -> Self {
        Self {
            offset: offset + self.offset,
            ..self
        }
    }

    /// Builds a new structure with foreground color set to the specified value
    pub fn with_fg(self, fg_color: Color) -> Self {
        Self { fg_color, ..self }
    }

    /// Builds a new structure with background color set to the specified value
    pub fn with_bg(self, bg_color: Color) -> Self {
        Self { bg_color, ..self }
    }

    /// Builds a new structure with alpha set to the specified value
    pub fn with_alpha(self, alpha: u8) -> Self {
        Self { alpha, ..self }
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
