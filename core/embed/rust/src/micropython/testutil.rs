extern "C" {
    fn gc_init(start: *mut cty::c_void, end: *mut cty::c_void);
    fn mp_stack_ctrl_init();
    fn mp_stack_set_limit(limit: usize);
    fn mp_init();
}

static mut HEAP: [u8; 20 * 1024 * 1024] = [0; 20 * 1024 * 1024];
static mut MPY_INITIALIZED: bool = false;

/// Initialize the MicroPython environment.
///
/// This is very hacky, in no way safe, and should not be used in production.
/// The stack is configured on a best-effort basis and depending on from where
/// this is called, you might get errorneous "recursion exceeded" problems.
///
/// This should only be called at start of your test function.
#[cfg(test)]
pub unsafe fn mpy_init() {
    unsafe {
        if MPY_INITIALIZED {
            return;
        }
        mp_stack_ctrl_init();
        mp_stack_set_limit(6000000);
        gc_init(
            HEAP.as_mut_ptr().cast(),
            HEAP.as_mut_ptr().add(HEAP.len()).cast(),
        );
        mp_init();
        MPY_INITIALIZED = true;
    }
}
