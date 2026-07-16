use crate::ffi;
use crate::util::FatPtr;

pub fn system_exit() -> ! {
    // SAFETY: safe
    unsafe { ffi::system_exit(0) }
}

pub fn system_exit_error(title: Option<&str>, message: &str, footer: Option<&str>) -> ! {
    let message_ptr = FatPtr::from(message);
    let title_ptr = title.map(FatPtr::from).unwrap_or_else(FatPtr::null);
    let footer_ptr = footer.map(FatPtr::from).unwrap_or_else(FatPtr::null);

    // SAFETY: safe
    unsafe {
        ffi::system_exit_error_ex(
            title_ptr.ptr(),
            title_ptr.len(),
            message_ptr.ptr(),
            message_ptr.len(),
            footer_ptr.ptr(),
            footer_ptr.len(),
        )
    }
}

#[inline(never)] // saves few kilobytes of flash
pub fn system_exit_fatal(message: &str, file: &str, line: u32) -> ! {
    let message_ptr = FatPtr::from(message);
    let file_ptr = FatPtr::from(file);

    // SAFETY: safe
    unsafe {
        ffi::system_exit_fatal_ex(
            message_ptr.ptr(),
            message_ptr.len(),
            file_ptr.ptr(),
            file_ptr.len(),
            line as i32,
        )
    }
}
