use super::ffi;

// SAFETY: Returned slice is valid and immutable until a call to `erase()`
// and/or `set_blob()`. Caller is responsible for disposing of all references to
// the slice before touching the flash contents.
pub unsafe fn get_blob<'a>() -> &'a [u8] {
    let mut len: u32 = 0;
    let ptr = unsafe { ffi::translations_read(&mut len, 0) };
    if ptr.is_null() {
        fatal_error!("Translations read failed");
    }
    // SAFETY: The pointer is always valid.
    unsafe { core::slice::from_raw_parts(ptr, len as usize) }
}

// SAFETY: This call invalidates the reference to the blob returned by
// `get_blob()`.
pub unsafe fn erase() {
    unsafe { ffi::translations_erase() };
}

pub fn area_bytesize() -> usize {
    // SAFETY: Safe, no side effects.
    unsafe { ffi::translations_area_bytesize() as usize }
}

// SAFETY: This call may invalidate the reference to the blob returned by
// `get_blob()`.
pub unsafe fn write(data: &[u8], offset: usize) -> bool {
    unsafe { ffi::translations_write(data.as_ptr(), offset as u32, data.len() as u32) }
}
