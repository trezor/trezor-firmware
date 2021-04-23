use cstr_core::CStr;

use super::ffi;

pub fn raise_value_error(msg: &'static CStr) -> ! {
    unsafe {
        ffi::mp_raise_ValueError(msg.as_ptr());
    }
    panic!();
}
