use super::ffi::{MODEL_FULL_NAME, MODEL_INTERNAL_NAME};

// TODO: get bindgen to do this for us more safely
// https://github.com/rust-lang/rust-bindgen/issues/1401

const unsafe fn ascii_const_to_str_unchecked(s: &[u8]) -> &str {
    unsafe {
        let strip_nul = core::slice::from_raw_parts(s.as_ptr(), s.len() - 1);
        core::str::from_utf8_unchecked(strip_nul)
    }
}

pub const FULL_NAME: &str = unsafe { ascii_const_to_str_unchecked(MODEL_FULL_NAME) };
pub const INTERNAL_NAME: &str = unsafe { ascii_const_to_str_unchecked(MODEL_INTERNAL_NAME) };
