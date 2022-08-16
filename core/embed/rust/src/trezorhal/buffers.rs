use super::ffi;

pub use ffi::{
    buffer_text_t as BufferText, line_buffer_16bpp_t as LineBuffer16Bpp,
    line_buffer_4bpp_t as LineBuffer4Bpp,
};

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
