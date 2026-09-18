use core::alloc::{GlobalAlloc, Layout};
#[cfg(feature = "debug")]
use core::sync::atomic::{AtomicUsize, Ordering};

use cty::c_void;

use super::ffi;

struct TrackedAllocator;

#[cfg(feature = "debug")]
static TOTAL: AtomicUsize = AtomicUsize::new(0);

// TODO: allow allocations only in an explicit scope?

unsafe impl GlobalAlloc for TrackedAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let size = layout.size();
        // TODO: SAFETY?
        let raw: *mut c_void = unsafe { ffi::m_tracked_calloc(1, size) };
        // TODO: use fallible allocator?
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
        raw as _
    }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        let raw: *mut c_void = ptr as _;
        let size = layout.size();
        // TODO: SAFETY?
        #[cfg(feature = "debug")]
        log::trace!(
            "{:?} = {} : -{}",
            raw,
            TOTAL.fetch_sub(size, Ordering::Relaxed),
            size
        );
        unsafe { ffi::m_tracked_free(raw) };
    }
}

#[global_allocator]
static ALLOCATOR: TrackedAllocator = TrackedAllocator;
