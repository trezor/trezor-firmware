use super::ffi;


pub fn play(effect: u8) {
    unsafe { ffi::haptic_play(effect as _) }
}
