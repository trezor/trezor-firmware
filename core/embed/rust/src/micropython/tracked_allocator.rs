use core::alloc::{GlobalAlloc, Layout};
use core::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

use cty::c_void;

use super::ffi;

pub struct TrackedAllocator;

static TOTAL: AtomicUsize = AtomicUsize::new(0);

static PEAK: AtomicUsize = AtomicUsize::new(0);

static ENABLE: AtomicBool = AtomicBool::new(false);

/// All heap allocations must happen within the `with_alloc` context.
/// Only single-threaded usage is supported.
pub fn with_alloc<F, R>(f: F) -> R
where
    F: FnOnce() -> R,
{
    ensure!(
        !ENABLE.swap(true, Ordering::Relaxed),
        "Allocator must be disabled"
    );
    ensure!(TOTAL.load(Ordering::Relaxed) == 0, "Leak detected");
    PEAK.store(0, Ordering::Relaxed);

    let result = f();

    log::trace!("Peak heap usage: {}", PEAK.load(Ordering::Relaxed));
    ensure!(
        ENABLE.swap(false, Ordering::Relaxed),
        "Allocator must be enabled"
    );
    // The result must not own heap memory, hence TOTAL should be zero.
    ensure!(TOTAL.load(Ordering::Relaxed) == 0, "Leak detected");

    result
}

unsafe impl GlobalAlloc for TrackedAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        ensure!(ENABLE.load(Ordering::Relaxed), "Disabled allocator");

        let size = layout.size();
        // SAFETY:
        //  - Unfortunately we cannot respect `layout.align()` as MicroPython GC does
        //    not support custom alignment.
        //  - `raw` is guaranteed to stay valid as long as `m_tracked_free()` is not
        //    called.
        // EXCEPTION:
        // - Terminates with a fatal error if allocation fails (better UX, instead of an
        //   internal Rust stdlib panic).
        let raw: *mut c_void = unsafe { ffi::m_tracked_calloc(1, size) };

        ensure!(!raw.is_null(), "Allocation failed");
        TOTAL.fetch_add(size, Ordering::Relaxed);
        PEAK.fetch_max(TOTAL.load(Ordering::Relaxed), Ordering::Relaxed);
        ensure!(raw.is_aligned_to(layout.align()), "Unaligned allocation");

        raw as _
    }
    unsafe fn dealloc(&self, ptr: *mut u8, _layout: Layout) {
        ensure!(ENABLE.load(Ordering::Relaxed), "Disabled allocator");
        let raw = ptr as *mut c_void;
        TOTAL.fetch_sub(_layout.size(), Ordering::Relaxed);

        // SAFETY: We are the sole owner of the allocated value.
        unsafe { ffi::m_tracked_free(raw) };
    }
}
