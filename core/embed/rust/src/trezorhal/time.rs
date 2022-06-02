use crate::time::Duration;

extern "C" {
    fn mp_hal_ticks_ms() -> cty::c_uint;
    fn mp_hal_delay_ms(delay: cty::c_uint);
}

pub fn ticks_ms() -> u32 {
    unsafe { mp_hal_ticks_ms() as _ }
}

pub fn sleep(delay: Duration) {
    unsafe { mp_hal_delay_ms(delay.to_millis() as _) }
}
