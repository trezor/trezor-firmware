use super::ffi;

pub fn dma2d_setup_4bpp_over_4bpp(fg_color: u16, bg_color: u16, overlay_color: u16) {
    unsafe { ffi::dma2d_setup_4bpp_over_4bpp(fg_color, bg_color, overlay_color) }
}

pub fn dma2d_setup_4bpp_over_16bpp(overlay_color: u16) {
    unsafe { ffi::dma2d_setup_4bpp_over_16bpp(overlay_color) }
}

pub fn dma2d_start_blend(overlay_buffer: &[u8], bg_buffer: &[u8], pixels: i16) {
    unsafe {
        ffi::dma2d_start_blend(
            overlay_buffer.as_ptr() as _,
            bg_buffer.as_ptr() as _,
            ffi::DISPLAY_DATA_ADDRESS as _,
            pixels as _,
        );
    }
}

pub fn dma2d_wait_for_transfer() {
    unsafe {
        ffi::dma2d_wait_for_transfer();
    }
}
