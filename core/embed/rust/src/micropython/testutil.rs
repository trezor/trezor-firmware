extern "C" {
    fn gc_init(start: *mut cty::c_void, end: *mut cty::c_void);
    fn mp_stack_set_top(top: *mut cty::c_void);
    fn mp_stack_set_limit(limit: usize);
    fn mp_init();
}

static mut HEAP: [u8; 20 * 1024 * 1024] = [0; 20 * 1024 * 1024];
static mut MPY_INITIALIZED: bool = false;

/// Initialize the MicroPython environment.
///
/// This is very hacky, in no way safe, and should not be used in production.
/// The stack is configured to span all of memory, effectively disabling the
/// stack guard. I have no idea what can happen.
///
/// This should only be called at start of your test function.
#[cfg(test)]
pub unsafe fn mpy_init() {
    unsafe {
        if MPY_INITIALIZED {
            return;
        }
        mp_stack_set_top(usize::MAX as *mut cty::c_void);
        mp_stack_set_limit(usize::MAX);
        gc_init(
            HEAP.as_mut_ptr().cast(),
            HEAP.as_mut_ptr().add(HEAP.len()).cast(),
        );
        mp_init();
        MPY_INITIALIZED = true;
    }
}
