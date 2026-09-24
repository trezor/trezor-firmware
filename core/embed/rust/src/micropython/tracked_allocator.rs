use core::alloc::{GlobalAlloc, Layout};
#[cfg(feature = "debug")]
use core::sync::atomic::{AtomicUsize, Ordering};

use cty::c_void;

use super::ffi;

pub struct TrackedAllocator;

#[cfg(feature = "debug")]
static TOTAL: AtomicUsize = AtomicUsize::new(0);

// TODO: allow allocations only in an explicit scope?

unsafe impl GlobalAlloc for TrackedAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let size = layout.size();
        // SAFETY:
        //  - Unfortunately we cannot respect `layout.align()` as MicroPython GC does
        //    not support custom alignment.
        //  - `raw` is guaranteed to stay valid as long as `m_tracked_free()` is not
        //    called.
        // EXCEPTION: Returns null instead of raising.
        let raw: *mut c_void = unsafe { ffi::m_tracked_calloc(1, size) };
        if raw.is_null() {
            log::error!("Cannot allocate {:?}", size);
            fatal_error!("m_tracked_calloc failed");
        }
        #[cfg(feature = "debug")]
        log::trace!(
            "{:?} = {} : +{}",
            raw,
            TOTAL.fetch_add(size, Ordering::Relaxed),
            size
        );
        ensure!(raw.is_aligned_to(layout.align()), "Unaligned allocation");
        raw as _
    }
    unsafe fn dealloc(&self, ptr: *mut u8, _layout: Layout) {
        let raw: *mut c_void = ptr as _;
        #[cfg(feature = "debug")]
        {
            let size = _layout.size();
            log::trace!(
                "{:?} = {} : -{}",
                raw,
                TOTAL.fetch_sub(size, Ordering::Relaxed),
                size
            );
        }
        // SAFETY: We are the sole owner of the allocated value.
        unsafe { ffi::m_tracked_free(raw) };
    }
}
