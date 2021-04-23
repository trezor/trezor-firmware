use cstr_core::CStr;

extern "C" {
    // trezorhal/common.c
    fn __fatal_error(
        expr: *const cty::c_char,
        msg: *const cty::c_char,
        file: *const cty::c_char,
        line: i32,
        func: *const cty::c_char,
    ) -> !;
}

pub fn fatal_error(expr: &CStr, msg: &CStr, file: &CStr, line: i32, func: &CStr) -> ! {
    unsafe {
        __fatal_error(
            expr.as_ptr(),
            msg.as_ptr(),
            file.as_ptr(),
            line,
            func.as_ptr(),
        );
    }
}
