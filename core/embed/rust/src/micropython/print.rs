use super::ffi;

/// Print a slice into emulator console.
/// Is being '\0' terminated automatically.
pub fn print(to_log: &str) {
    unsafe {
        ffi::mp_print_strn(
            &ffi::mp_plat_print,
            to_log.as_ptr() as _,
            to_log.len(),
            0,
            '\0' as _,
            0,
        );
    }
}
