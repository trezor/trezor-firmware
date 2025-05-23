// Copyright (c) 2025 Trezor Company s.r.o.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

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
