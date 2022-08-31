use super::ffi;
use core::{ffi::CStr, mem::MaybeUninit, ptr};

pub use ffi::{FATFS, FIL, FRESULT};

impl Default for ffi::FATFS {
    fn default() -> Self {
        unsafe { MaybeUninit::<Self>::zeroed().assume_init() }
    }
}

impl Default for ffi::FIL {
    fn default() -> Self {
        unsafe { MaybeUninit::<Self>::zeroed().assume_init() }
    }
}

fn process_result(res: FRESULT) -> Result<(), FRESULT> {
    if res == ffi::FRESULT_FR_OK {
        Ok(())
    } else {
        Err(res)
    }
}

pub fn mount(fs: &mut FATFS) -> Result<(), FRESULT> {
    unsafe {
        process_result(ffi::f_mount(
            fs,
            CStr::from_bytes_with_nul_unchecked(b"\0").as_ptr() as _,
            1,
        ))
    }
}

pub fn unmount() -> Result<(), FRESULT> {
    unsafe {
        process_result(ffi::f_mount(
            ptr::null_mut(),
            CStr::from_bytes_with_nul_unchecked(b"\0").as_ptr() as _,
            0,
        ))
    }
}

pub fn open(fil: &mut FIL, path: &str, mode: u8) -> Result<(), FRESULT> {
    unsafe {
        process_result(ffi::f_open(
            fil,
            CStr::from_bytes_with_nul_unchecked(path.as_bytes()).as_ptr() as _,
            mode as _,
        ))
    }
}

pub fn close(fil: &mut FIL) -> Result<(), FRESULT> {
    unsafe { process_result(ffi::f_close(fil)) }
}

pub fn read(fil: &mut FIL, buff: &mut [u8]) -> Result<u32, FRESULT> {
    unsafe {
        let mut bytes_read: u32 = 0;

        let result = ffi::f_read(fil, buff.as_ptr() as _, buff.len() as _, &mut bytes_read);
        {
            if result == ffi::FRESULT_FR_OK {
                Ok(bytes_read)
            } else {
                Err(result)
            }
        }
    }
}

pub fn unlink(path: &str) -> Result<(), FRESULT> {
    unsafe {
        process_result(ffi::f_unlink(
            CStr::from_bytes_with_nul_unchecked(path.as_bytes()).as_ptr() as _,
        ))
    }
}

pub fn rename(path_old: &str, path_new: &str) -> Result<(), FRESULT> {
    unsafe {
        process_result(ffi::f_rename(
            CStr::from_bytes_with_nul_unchecked(path_old.as_bytes()).as_ptr() as _,
            CStr::from_bytes_with_nul_unchecked(path_new.as_bytes()).as_ptr() as _,
        ))
    }
}
