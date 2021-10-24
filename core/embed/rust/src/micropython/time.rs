use super::ffi;

pub fn ticks_ms() -> u32 {
    unsafe { ffi::mp_hal_ticks_ms() as _ }
}
