use core::alloc::Layout;

use talc::base::Talc;
use trezor_app_sdk::traits::allocator as alloc_traits;

/// Core's only Rust heap, and its `#[global_allocator]` (`TalcLock`
/// implements `GlobalAlloc` directly). Core itself is alloc-free — it never
/// holds live Rust-heap state of its own, so this exists purely to back
/// [`AllocatorProxy`], i.e. the allocator loaded apps use (via the API
/// vtable). Rebuilt from scratch (not reused) on every app launch; see
/// [`init`] for why — `TalcLock::lock()` hands out a guard that derefs to
/// the inner `Talc`, so `*lock = Talc::new(..)` replaces the whole value in
/// place, same as it would through a plain `Mutex`.
#[global_allocator]
static APP_ALLOCATOR: talc::TalcLock<spin::Mutex<()>, talc::source::Manual> =
    talc::TalcLock::new(talc::source::Manual);

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
    // `rkyv`'s `to_bytes`/`to_bytes_in` cache a scratch `Arena` in this
    // thread's thread-local storage, backed by the global allocator, and
    // reuse it across calls for efficiency. The task's underlying OS thread
    // outlives any single app launch (it's the same thread that just called a
    // freshly `dlopen`ed app's new entry point), so without this, the next
    // app's first `rkyv::to_bytes` call would reuse a block pointer that was
    // allocated by the *previous* `Talc` instance. Must run before that old
    // instance is discarded below: dropping the arena deallocates its block
    // through the *current* global allocator, so the old `Talc` instance
    // needs to still be live to see a deallocation matching what it handed
    // out — freeing it against a freshly-`claim`ed instance instead corrupts
    // that instance's bookkeeping.
    rkyv::util::clear_arena();

    let (heap_base, heap_size) = io::get_heap();

    let mut allocator = APP_ALLOCATOR.lock();
    *allocator = Talc::new(talc::source::Manual);
    unsafe {
        allocator
            .claim(heap_base, heap_size)
            .expect("failed to claim heap for the app allocator");
    }
}

/// The allocator loaded apps use, exposed to them through the API vtable
/// ([`alloc_traits::GlobalAllocatorV1`]). Just forwards to [`APP_ALLOCATOR`],
/// which is also Core's own `#[global_allocator]`.
pub struct AllocatorProxy;

unsafe impl alloc_traits::GlobalAllocatorV1 for AllocatorProxy {
    unsafe extern "C" fn alloc(&self, layout: alloc_traits::FfiLayout) -> *mut u8 {
        // SAFETY: caller upholds `GlobalAllocatorV1::alloc`'s contract.
        unsafe {
            APP_ALLOCATOR
                .lock()
                .allocate(Layout::from(layout))
                .map_or(core::ptr::null_mut(), |ptr| ptr.as_ptr())
        }
    }

    unsafe extern "C" fn dealloc(&self, ptr: *mut u8, layout: alloc_traits::FfiLayout) {
        // SAFETY: caller upholds `GlobalAllocatorV1::dealloc`'s contract.
        unsafe { APP_ALLOCATOR.lock().deallocate(ptr, Layout::from(layout)) }
    }

    unsafe extern "C" fn alloc_zeroed(&self, layout: alloc_traits::FfiLayout) -> *mut u8 {
        let layout = Layout::from(layout);
        // SAFETY: caller upholds `GlobalAllocatorV1::alloc_zeroed`'s contract.
        let ptr = unsafe {
            APP_ALLOCATOR
                .lock()
                .allocate(layout)
                .map_or(core::ptr::null_mut(), |ptr| ptr.as_ptr())
        };
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
        let layout = Layout::from(layout);
        let Ok(new_layout) = Layout::from_size_align(new_size, layout.align()) else {
            return core::ptr::null_mut();
        };
        // SAFETY: caller upholds `GlobalAllocatorV1::realloc`'s contract.
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
}
