unsafe extern "C" {
    fn gc_init(start: *mut cty::c_void, end: *mut cty::c_void);
    fn mp_stack_set_top(top: *mut cty::c_void);
    fn mp_stack_set_limit(limit: usize);
    fn mp_init();
}

const HEAP_SIZE_WORDS: usize = 20 * 1024 * 1024 / core::mem::size_of::<usize>();
static mut HEAP: [usize; HEAP_SIZE_WORDS] = [0; HEAP_SIZE_WORDS];
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
    let heap_ptr = core::ptr::addr_of_mut!(HEAP) as *mut usize;
    unsafe {
        if MPY_INITIALIZED {
            return;
        }
        MPY_INITIALIZED = true;
        mp_stack_set_top(usize::MAX as *mut cty::c_void);
        mp_stack_set_limit(usize::MAX);
        gc_init(heap_ptr.cast(), heap_ptr.add(HEAP_SIZE_WORDS).cast());
        mp_init();
    }
}
