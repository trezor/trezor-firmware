use core::alloc::Layout;

use talc::base::Talc;
use trezor_app_sdk::traits::allocator as alloc_traits;

/// Core's only Rust heap. Core itself is alloc-free — it never holds live
/// Rust-heap state of its own, so this exists purely to back
/// [`AllocatorProxy`], i.e. the allocator loaded apps use (via the API
/// vtable). Rebuilt from scratch (not reused) on every app launch; see
/// [`init`] for why.
///
/// A plain `Talc` behind our own lock, rather than a `talc::TalcLock`: a
/// `TalcLock` bundles its own inner mutex, which would leave no way to
/// replace the *whole* `Talc` value — only to call methods on the one
/// instance that's lived there since boot.
static APP_ALLOCATOR: spin::Mutex<Talc<talc::source::Manual, talc::DefaultBinning>> =
    spin::Mutex::new(Talc::new(talc::source::Manual));

/// Gives [`APP_ALLOCATOR`] a backing memory region to allocate from: the
/// real, manifest-sized heap the loader carved out for the currently active
/// applet (via `app_get_heap`).
///
/// Must be called once per app launch, not just once ever — the loaded app
/// is always the same kernel task id, so without resetting the allocator
/// first, every app after the first would keep allocating out of whichever
/// app's heap region was claimed first.
///
/// Rebuilds [`APP_ALLOCATOR`] as a brand new `Talc` rather than reusing the
/// existing one via `truncate`/`claim`: a killed app is never given the
/// chance to free its live allocations (its task is just torn down), so
/// from `Talc`'s point of view the previous heap can still have "allocated"
/// chunks blocking a full `truncate`. Worse, `Talc`'s own bookkeeping
/// (`gap_lists`, the bin-list array `claim` sets up on a heap's first use)
/// lives *inside* the very heap memory it manages — reusing the same `Talc`
/// instance across app launches, on the exact same physical arena, means a
/// `truncate` that can't fully clear that region leaves `Talc` still
/// pointing at bookkeeping structures that are about to be handed out as
/// regular allocations by the next `claim`, corrupting the allocator.
/// Discarding the whole `Talc` value sidesteps this: a freshly constructed
/// `Talc` has never claimed anything, so `claim` always takes its "first
/// heap ever" path and rebuilds that bookkeeping from scratch.
pub fn init() {
    let (heap_base, heap_size) = io::get_heap();

    let mut allocator = APP_ALLOCATOR.lock();
    *allocator = Talc::new(talc::source::Manual);
    unsafe {
        allocator
            .claim(heap_base, heap_size)
            .expect("failed to claim heap for the app allocator");
    }
}

unsafe fn raw_alloc(layout: Layout) -> *mut u8 {
    unsafe {
        APP_ALLOCATOR
            .lock()
            .allocate(layout)
            .map_or(core::ptr::null_mut(), |ptr| ptr.as_ptr())
    }
}

unsafe fn raw_dealloc(ptr: *mut u8, layout: Layout) {
    unsafe { APP_ALLOCATOR.lock().deallocate(ptr, layout) }
}

unsafe fn raw_realloc(ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
    let Ok(new_layout) = Layout::from_size_align(new_size, layout.align()) else {
        return core::ptr::null_mut();
    };
    unsafe {
        let mut allocator = APP_ALLOCATOR.lock();
        let Some(new_ptr) = allocator.allocate(new_layout) else {
            return core::ptr::null_mut();
        };
        let copy_size = core::cmp::min(layout.size(), new_size);
        core::ptr::copy_nonoverlapping(ptr, new_ptr.as_ptr(), copy_size);
        allocator.deallocate(ptr, layout);
        new_ptr.as_ptr()
    }
}

/// Doubles as Core's `#[global_allocator]` below and as the allocator loaded
/// apps use, exposed to them through the API vtable ([`alloc_traits::GlobalAllocatorV1`]).
/// Both sides just forward to [`APP_ALLOCATOR`].
pub struct AllocatorProxy;

unsafe impl alloc_traits::GlobalAllocatorV1 for AllocatorProxy {
    unsafe extern "C" fn alloc(&self, layout: alloc_traits::FfiLayout) -> *mut u8 {
        unsafe { raw_alloc(Layout::from(layout)) }
    }

    unsafe extern "C" fn dealloc(&self, ptr: *mut u8, layout: alloc_traits::FfiLayout) {
        unsafe { raw_dealloc(ptr, Layout::from(layout)) }
    }

    unsafe extern "C" fn alloc_zeroed(&self, layout: alloc_traits::FfiLayout) -> *mut u8 {
        let layout = Layout::from(layout);
        let ptr = unsafe { raw_alloc(layout) };
        if !ptr.is_null() {
            unsafe { ptr.write_bytes(0, layout.size()) };
        }
        ptr
    }

    unsafe extern "C" fn realloc(
        &self,
        ptr: *mut u8,
        layout: alloc_traits::FfiLayout,
        new_size: usize,
    ) -> *mut u8 {
        unsafe { raw_realloc(ptr, Layout::from(layout), new_size) }
    }
}

#[global_allocator]
static GLOBAL_ALLOCATOR: AllocatorProxy = AllocatorProxy;

unsafe impl core::alloc::GlobalAlloc for AllocatorProxy {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        unsafe { raw_alloc(layout) }
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        unsafe { raw_dealloc(ptr, layout) }
    }

    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        unsafe { raw_realloc(ptr, layout, new_size) }
    }
}
