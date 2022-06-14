use super::ffi;
use core::ptr;

pub const UZLIB_WINDOW_SIZE: usize = 1 << 10;
pub use ffi::uzlib_uncomp;

impl Default for ffi::uzlib_uncomp {
    fn default() -> Self {
        let mut s = ::core::mem::MaybeUninit::<Self>::uninit();
        unsafe {
            ptr::write_bytes(s.as_mut_ptr(), 0, 1);
            s.assume_init()
        }
    }
}

pub fn uzlib_prepare(
    decomp: &mut uzlib_uncomp,
    window: Option<&mut [u8]>,
    src: &[u8],
    dest: &mut [u8],
) {
    unsafe {
        decomp.source = src.as_ptr();
        decomp.source_limit = src.as_ptr().offset(src.len() as isize);
        decomp.dest = dest.as_mut_ptr();
        decomp.dest_limit = dest.as_mut_ptr().offset(dest.len() as isize);

        if let Some(w) = window {
            ffi::uzlib_uncompress_init(decomp, w.as_ptr() as _, w.len() as u32);
        } else {
            ffi::uzlib_uncompress_init(decomp, ptr::null_mut(), 0);
        }
    }
}

pub fn uzlib_uncompress(decomp: &mut uzlib_uncomp, dest: &mut [u8]) -> i32 {
    unsafe {
        decomp.dest = dest.as_mut_ptr();
        return ffi::uzlib_uncompress(decomp as _);
    }
}
