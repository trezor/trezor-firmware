use super::ffi;

pub use ffi::SHA256_DIGEST_LENGTH;

pub fn hmac_sha256(key: &[u8], msg: &[u8], result: &mut [u8]) {
    unsafe {
        assert_eq!(result.len(), SHA256_DIGEST_LENGTH as usize);
        ffi::hmac_sha256(
            key.as_ptr(),
            key.len() as _,
            msg.as_ptr(),
            msg.len() as _,
            result.as_mut_ptr(),
        )
    }
}
