use super::ffi;

#[allow(dead_code)]

pub fn dma2d_setup_const() {
    unsafe { ffi::dma2d_setup_const() }
}
pub fn dma2d_setup_4bpp(fg_color: u16, bg_color: u16) {
    unsafe { ffi::dma2d_setup_4bpp(fg_color, bg_color) }
}

pub fn dma2d_setup_16bpp() {
    unsafe { ffi::dma2d_setup_16bpp() }
}

pub fn dma2d_setup_4bpp_over_4bpp(fg_color: u16, bg_color: u16, overlay_color: u16) {
    unsafe { ffi::dma2d_setup_4bpp_over_4bpp(fg_color, bg_color, overlay_color) }
}

pub fn dma2d_setup_4bpp_over_16bpp(overlay_color: u16) {
    unsafe { ffi::dma2d_setup_4bpp_over_16bpp(overlay_color) }
}

/// Starts dma2d transfer
///
/// # Safety
///
/// This function is unsafe because the caller has to guarantee that he:
/// 1) doesn't mutate the buffers until the transfer is finished, which is
/// guaranteed by calling `dma2d_wait_for_transfer`
/// 2) the buffer doesn't get dropped until the transfer is finished
/// 3) doesn't call this function while another transfer is running
pub unsafe fn dma2d_start(buffer: &[u8], pixels: i16) {
    unsafe {
        ffi::dma2d_start(
            buffer.as_ptr() as _,
            ffi::display_get_wr_addr() as _,
            pixels as _,
        );
    }
}

/// Starts blending
///
/// # Safety
///
/// This function is unsafe because the caller has to guarantee that he:
/// 1) doesn't mutate the buffers until the transfer is finished, which is
/// guaranteed by calling `dma2d_wait_for_transfer`
/// 2) the buffer doesn't get dropped until the transfer is finished
/// 3) doesn't call this function while another transfer is running
pub unsafe fn dma2d_start_blend(overlay_buffer: &[u8], bg_buffer: &[u8], pixels: i16) {
    unsafe {
        ffi::dma2d_start_blend(
            overlay_buffer.as_ptr() as _,
            bg_buffer.as_ptr() as _,
            ffi::display_get_wr_addr() as _,
            pixels as _,
        );
    }
}

/// Starts blending
///
/// # Safety
///
/// This function is unsafe because the caller has to guarantee that he:
/// 1) doesn't mutate the buffers until the transfer is finished, which is
/// guaranteed by calling `dma2d_wait_for_transfer`
/// 2) the buffer doesn't get dropped until the transfer is finished
/// 3) doesn't call this function while another transfer is running
pub unsafe fn dma2d_start_const(color: u16, pixels: i16) {
    unsafe {
        ffi::dma2d_start_const(color, ffi::display_get_wr_addr() as _, pixels as _);
    }
}

#[cfg(feature = "framebuffer")]
/// Starts blending
///
/// # Safety
///
/// This function is unsafe because the caller has to guarantee that he:
/// 1) doesn't mutate the buffers until the transfer is finished, which is
/// guaranteed by calling `dma2d_wait_for_transfer`
/// 2) the buffer doesn't get dropped until the transfer is finished
/// 3) doesn't call this function while another transfer is running
pub unsafe fn dma2d_start_const_multiline(color: u16, width: i16, height: i16) {
    unsafe {
        ffi::dma2d_start_const_multiline(
            color,
            ffi::display_get_wr_addr() as _,
            width as _,
            height as _,
        );
    }
}

pub fn dma2d_wait_for_transfer() {
    unsafe {
        ffi::dma2d_wait_for_transfer();
    }
}
