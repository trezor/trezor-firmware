use crate::ui::{
    geometry::Offset,
    shape::{Bitmap, BitmapFormat},
};

/// Raw image buffer used by `ImageBuffer` instances.
static mut IMAGE_BUFFER: [u8; 64 * 1024] = [0; 64 * 1024];

/// Set to `true` if the `IMAGE_BUFFER` is locked
/// (in use by some instance of `ImageBuffer`)
static mut IMAGE_BUFFER_LOCKED: bool = false;

/// A struct representing an image buffer - generic buffer for mutable images.
pub struct ImageBuffer {
    bitmap: Bitmap<'static>,
}

impl Drop for ImageBuffer {
    fn drop(&mut self) {
        // It's safe to modify static variable as whole app
        // is single-threaded.
        unsafe {
            IMAGE_BUFFER_LOCKED = false;
        }
    }
}

impl ImageBuffer {
    /// Creates a new image buffer with the specified format and size.
    ///
    /// Returns `None` if the buffer is already in use or the
    /// buffer is not big enough to hold the image.
    pub fn new(format: BitmapFormat, size: Offset) -> Option<Self> {
        // SAFETY:
        // It's safe to read/modify mutable static variable as
        // whole app is single-threaded.
        //
        // We can be sure that `IMAGE_BUFFER` is not shared between
        // multiple instances of `ImageBuffer` as we have `IMAGE_BUFFER_LOCKED`
        // to prevent that.
        unsafe {
            if IMAGE_BUFFER_LOCKED {
                return None;
            }

            let bitmap = Bitmap::new_mut(format, None, size, None, &mut IMAGE_BUFFER[..])?;

            IMAGE_BUFFER_LOCKED = true;

            Some(Self { bitmap })
        }
    }

    /// Returns the mutable bitmap in the image buffer.
    pub fn bitmap_mut(&mut self) -> &mut Bitmap<'static> {
        &mut self.bitmap
    }

    /// Returns the immutable bitmap in the image buffer.
    pub fn bitmap(&mut self) -> &Bitmap<'static> {
        &self.bitmap
    }
}
