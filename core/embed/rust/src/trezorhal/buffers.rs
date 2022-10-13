use super::ffi;

pub use ffi::{
    buffer_blurring_t as BlurringBuffer, buffer_text_t as BufferText,
    line_buffer_16bpp_t as LineBuffer16Bpp, line_buffer_4bpp_t as LineBuffer4Bpp,
};
#[cfg(feature = "jpeg")]
pub use ffi::{buffer_jpeg_t as BufferJpeg, buffer_jpeg_work_t as BufferJpegWork};

/// Returns a buffer for one line of 16bpp data
///
/// # Safety
///
/// This function is unsafe because the caller has to guarantee
/// that he doesn't use buffer on same index multiple times
pub unsafe fn get_buffer_16bpp(idx: u16, clear: bool) -> &'static mut LineBuffer16Bpp {
    unsafe {
        let ptr = ffi::buffers_get_line_buffer_16bpp(idx, clear);
        unwrap!(ptr.as_mut())
    }
}

/// Returns a buffer for one line of 4bpp data
///
/// # Safety
///
/// This function is unsafe because the caller has to guarantee
/// that he doesn't use buffer on same index multiple times
pub unsafe fn get_buffer_4bpp(idx: u16, clear: bool) -> &'static mut LineBuffer4Bpp {
    unsafe {
        let ptr = ffi::buffers_get_line_buffer_4bpp(idx, clear);
        unwrap!(ptr.as_mut())
    }
}

/// Returns a buffer for one line of text
///
/// # Safety
///
/// This function is unsafe because the caller has to guarantee
/// that he doesn't use buffer on same index multiple times
pub unsafe fn get_text_buffer(idx: u16, clear: bool) -> &'static mut BufferText {
    unsafe {
        let ptr = ffi::buffers_get_text_buffer(idx, clear);
        unwrap!(ptr.as_mut())
    }
}

/// Returns a buffer for jpeg data
///
/// # Safety
///
/// This function is unsafe because the caller has to guarantee
/// that he doesn't use buffer on same index multiple times
#[cfg(feature = "jpeg")]
pub unsafe fn get_jpeg_buffer(idx: u16, clear: bool) -> &'static mut BufferJpeg {
    unsafe {
        let ptr = ffi::buffers_get_jpeg_buffer(idx, clear);
        unwrap!(ptr.as_mut())
    }
}

/// Returns a jpeg work buffer
///
/// # Safety
///
/// This function is unsafe because the caller has to guarantee
/// that he doesn't use buffer on same index multiple times
#[cfg(feature = "jpeg")]
pub unsafe fn get_jpeg_work_buffer(idx: u16, clear: bool) -> &'static mut BufferJpegWork {
    unsafe {
        let ptr = ffi::buffers_get_jpeg_work_buffer(idx, clear);
        unwrap!(ptr.as_mut())
    }
}

/// Returns a buffer for blurring data
///
/// # Safety
///
/// This function is unsafe because the caller has to guarantee
/// that he doesn't use buffer on same index multiple times
pub unsafe fn get_blurring_buffer(idx: u16, clear: bool) -> &'static mut BlurringBuffer {
    unsafe {
        let ptr = ffi::buffers_get_blurring_buffer(idx, clear);
        unwrap!(ptr.as_mut())
    }
}
