unsafe extern "C" {
    fn gc_init(start: *mut cty::c_void, end: *mut cty::c_void);
    fn mp_stack_set_top(top: *mut cty::c_void);
    fn mp_stack_set_limit(limit: usize);
    fn mp_init();
}

const HEAP_SIZE: usize = 20 * 1024 * 1024;
static mut HEAP: [u8; HEAP_SIZE] = [0; HEAP_SIZE];
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
    let heap_ptr = core::ptr::addr_of_mut!(HEAP);
    unsafe {
        if MPY_INITIALIZED {
            return;
        }
        mp_stack_set_top(usize::MAX as *mut cty::c_void);
        mp_stack_set_limit(usize::MAX);
        gc_init(heap_ptr.cast(), heap_ptr.add(HEAP_SIZE).cast());
        mp_init();
        MPY_INITIALIZED = true;
    }
}
