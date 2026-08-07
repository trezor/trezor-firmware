pub use ffi::irq_key_t as IrqKey;

use super::ffi;

pub fn irq_lock() -> IrqKey {
    unsafe { ffi::irq_lock_fn() }
}

pub fn irq_unlock(key: IrqKey) {
    unsafe {
        ffi::irq_unlock_fn(key);
    }
}
