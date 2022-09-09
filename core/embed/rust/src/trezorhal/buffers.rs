use super::ffi;

pub use ffi::{
    buffer_text_t as BufferText, line_buffer_16bpp_t as LineBuffer16Bpp,
    line_buffer_4bpp_t as LineBuffer4Bpp,
};

pub fn get_buffer_16bpp(idx: u16, clear: bool) -> &'static mut LineBuffer16Bpp {
    unsafe {
        let ptr = ffi::buffers_get_line_buffer_16bpp(idx, clear);
        assert!(!ptr.is_null());
        &mut *ptr
    }
}

pub fn get_buffer_4bpp(idx: u16, clear: bool) -> &'static mut LineBuffer4Bpp {
    unsafe {
        let ptr = ffi::buffers_get_line_buffer_4bpp(idx, clear);
        assert!(!ptr.is_null());
        &mut *ptr
    }
}

pub fn get_text_buffer(idx: u16, clear: bool) -> &'static mut BufferText {
    unsafe {
        let ptr = ffi::buffers_get_text_buffer(idx, clear);
        assert!(!ptr.is_null());
        &mut *ptr
    }
}
