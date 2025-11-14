use super::{echo, image_info, process_rx_byte, reset, upload};

use crate::util::from_c_array;

#[no_mangle]
extern "C" fn smp_echo(text: *const cty::c_char, text_len: u8) -> bool {
    let text = unwrap!(unsafe { from_c_array(text, text_len as usize) });

    echo::send(text)
}

#[no_mangle]
extern "C" fn smp_reset() {
    reset::send();
}

/// Get the nRF app version string.
///
/// # Arguments
/// * `version_buf` - Pointer to a C buffer to write the version string
/// * `buf_len` - Size of the buffer
///
/// # Returns
/// The number of bytes written (excluding null terminator), or 0 on error.
/// The string will be null-terminated if it fits in the buffer.
#[no_mangle]
extern "C" fn smp_image_version_get(
    version_buf: *mut cty::c_char,
    buf_len: cty::size_t,
) -> cty::size_t {
    if version_buf.is_null() || buf_len == 0 {
        return 0;
    }

    unsafe {
        // Create a mutable slice from the C buffer
        let rust_buf = core::slice::from_raw_parts_mut(version_buf as *mut u8, buf_len);

        // Reserve space for null terminator
        if buf_len > 0 {
            let result_len = image_info::get_version(&mut rust_buf[..buf_len - 1]);

            if result_len > 0 {
                // Add null terminator
                rust_buf[result_len] = 0;
                return result_len as cty::size_t;
            }
        }

        0
    }
}

#[no_mangle]
extern "C" fn smp_upload_app_image(
    data: *const cty::uint8_t,
    len: cty::size_t,
    image_hash: *const cty::uint8_t,
    image_hash_len: cty::size_t,
) -> bool {
    let data_slice = unsafe { core::slice::from_raw_parts(data, len) };
    let hash_slice = unsafe { core::slice::from_raw_parts(image_hash, image_hash_len) };

    upload::upload_image(data_slice, hash_slice)
}

#[no_mangle]
extern "C" fn smp_process_rx_byte(byte: u8) {
    process_rx_byte(byte)
}
