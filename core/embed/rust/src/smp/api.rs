use super::{echo, process_rx_byte, reset, upload};

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
