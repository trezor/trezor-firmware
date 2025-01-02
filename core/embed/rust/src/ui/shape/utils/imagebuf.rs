use crate::{
    error::Error,
    ui::{
        geometry::Offset,
        shape::{Bitmap, BitmapView, Canvas, CanvasBuilder},
    },
};

/// Size of image buffer in bytes
/// (up to 240x240 pixel, 16-bit RGB565 image)
const IMAGE_BUFFER_SIZE: usize = 240 * 240 * 2;

#[repr(align(16))]
struct AlignedBuffer {
    bytes: [u8; IMAGE_BUFFER_SIZE],
}

/// Raw image buffer used by `ImageBuffer` instances.

static mut IMAGE_BUFFER: AlignedBuffer = AlignedBuffer {
    bytes: [0; IMAGE_BUFFER_SIZE],
};

/// Set to `true` if the `IMAGE_BUFFER` is locked
/// (in use by some instance of `ImageBuffer`)
static mut IMAGE_BUFFER_LOCKED: bool = false;

/// A struct representing an image buffer - generic buffer for mutable images.
pub struct ImageBuffer<T: Canvas + CanvasBuilder<'static>> {
    canvas: T,
}

impl<T> Drop for ImageBuffer<T>
where
    T: Canvas + CanvasBuilder<'static>,
{
    fn drop(&mut self) {
        // It's safe to modify static variable as whole app
        // is single-threaded.
        unsafe {
            IMAGE_BUFFER_LOCKED = false;
        }
    }
}

impl<T> ImageBuffer<T>
where
    T: Canvas + CanvasBuilder<'static>,
{
    /// Creates a new image buffer with the specified format and size.
    ///
    /// Returns `None` if the buffer is already in use or the
    /// buffer is not big enough to hold the image.
    pub fn new(size: Offset) -> Result<Self, Error> {
        // SAFETY:
        // It's safe to read/modify mutable static variable as
        // whole app is single-threaded.
        //
        // We can be sure that `IMAGE_BUFFER` is not shared between
        // multiple instances of `ImageBuffer` as we have `IMAGE_BUFFER_LOCKED`
        // to prevent that.
        unsafe {
            if IMAGE_BUFFER_LOCKED {
                return Err(Error::AllocationFailed);
            }

            let bitmap =
                Bitmap::new_mut(T::format(), None, size, None, &mut IMAGE_BUFFER.bytes[..])?;

            IMAGE_BUFFER_LOCKED = true;

            Ok(Self {
                canvas: T::from_bitmap(bitmap),
            })
        }
    }

    /// Returns the canvas for the bitmap in the image buffer.
    pub fn canvas(&mut self) -> &mut T {
        &mut self.canvas
    }

    /// Returns the immutable view of the bitmap in the image buffer.
    pub fn view(&self) -> BitmapView {
        self.canvas.view()
    }
}
