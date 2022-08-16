use super::ffi;
use core::slice::from_raw_parts_mut;

#[cfg(feature = "dma2d")]
pub fn dma2d_setup_4bpp_over_4bpp(fg_color: u16, bg_color: u16, overlay_color: u16) {
    unsafe { ffi::dma2d_setup_4bpp_over_4bpp(fg_color, bg_color, overlay_color) }
}

#[cfg(feature = "dma2d")]
pub fn dma2d_setup_4bpp_over_16bpp(overlay_color: u16) {
    unsafe { ffi::dma2d_setup_4bpp_over_16bpp(overlay_color) }
}

#[cfg(feature = "dma2d")]
pub fn dma2d_start_blend(overlay_buffer: &[u8], bg_buffer: &[u8], pixels: i32) {
    unsafe {
        ffi::dma2d_start_blend(
            overlay_buffer.as_ptr() as _,
            bg_buffer.as_ptr() as _,
            ffi::DISPLAY_DATA_ADDRESS as _,
            pixels,
        );
    }
}

#[cfg(feature = "dma2d")]
pub fn dma2d_wait_for_transfer() {
    unsafe {
        ffi::dma2d_wait_for_transfer();
    }
}

pub fn get_buffer_16bpp(idx: u16, clear: bool) -> &'static mut [u8] {
    unsafe {
        let ptr = ffi::buffers_get_line_buffer_16bpp(idx, clear);
        assert!(!ptr.is_null());
        from_raw_parts_mut(ptr, (ffi::buffer_width * 2) as usize)
    }
}

pub fn get_buffer_4bpp(idx: u16, clear: bool) -> &'static mut [u8] {
    unsafe {
        let ptr = ffi::buffers_get_line_buffer_4bpp(idx, clear);
        assert!(!ptr.is_null());
        from_raw_parts_mut(ptr, (ffi::buffer_width / 2) as usize)
    }
}

pub fn get_text_buffer(idx: u16, clear: bool) -> &'static mut [u8] {
    unsafe {
        let ptr = ffi::buffers_get_text_buffer(idx, clear);
        assert!(!ptr.is_null());
        from_raw_parts_mut(
            ptr,
            (ffi::buffer_width * ffi::text_buffer_height / 2) as usize,
        )
    }
}
