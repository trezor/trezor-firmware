use cstr_core::CStr;

extern "C" {
    // micropython/runtime.c
    fn mp_raise_ValueError(msg: *const cty::c_char) -> !;
}

pub fn raise_value_error(msg: &'static CStr) -> ! {
    unsafe { mp_raise_ValueError(msg.as_ptr()) }
}
