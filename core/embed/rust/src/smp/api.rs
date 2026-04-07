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

#[repr(C, packed)]
pub struct NrfAppVersion {
    pub major: u8,
    pub minor: u8,
    pub revision: u16,
    pub build_num: u32,
}

/// Get the nRF app version as parsed integer components.
///
/// Sends an SMP request to the nRF device to retrieve the active application
/// image version, then parses the version string into individual numeric
/// components.
///
/// # Arguments
/// * `out` - Pointer to NrfAppVersion structure to be filled. Must not be NULL.
///
/// # Returns
/// `true` if version was successfully retrieved and parsed, `false` otherwise.
#[no_mangle]
extern "C" fn smp_image_version_get(out: *mut NrfAppVersion) -> bool {
    if out.is_null() {
        return false;
    }
    match image_info::get_version_numbers() {
        Some(v) => {
            unsafe {
                (*out).major = v.major;
                (*out).minor = v.minor;
                (*out).revision = v.revision;
                (*out).build_num = v.build_num;
            }
            true
        }
        None => false,
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
