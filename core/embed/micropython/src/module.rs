use super::ffi;

pub type Module = ffi::mp_obj_module_t;

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Module {}
