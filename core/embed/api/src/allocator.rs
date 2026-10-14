use core::alloc::{GlobalAlloc, Layout};
use core::ptr::null_mut;

use trezor_app_sdk::traits::allocator as alloc_traits;

use crate::app_state;

/// Core's `#[global_allocator]`, and the allocator loaded apps use via the API
/// vtable ([`AllocatorProxy`]).
///
/// Stateless: it allocates from the heap of the app running on the current
/// task, through the `Talc` in that app's [`app_state::AppState`]. Core itself
/// is alloc-free, so on a task without an app every allocation fails.
struct AppAllocator;

#[global_allocator]
static APP_ALLOCATOR: AppAllocator = AppAllocator;

unsafe impl GlobalAlloc for AppAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let Some(state) = app_state::try_get() else {
            return null_mut();
        };
        // SAFETY: caller upholds `GlobalAlloc::alloc`'s contract.
        unsafe { state.allocator.lock().allocate(layout) }.map_or(null_mut(), |ptr| ptr.as_ptr())
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        // SAFETY: caller upholds `GlobalAlloc::dealloc`'s contract; `ptr` was
        // allocated on this task, so its app state exists.
        unsafe { app_state::get().allocator.lock().deallocate(ptr, layout) }
    }
}

/// The allocator loaded apps use, exposed to them through the API vtable
/// ([`alloc_traits::GlobalAllocatorV1`]). Just forwards to [`APP_ALLOCATOR`].
pub struct AllocatorProxy;

unsafe impl alloc_traits::GlobalAllocatorV1 for AllocatorProxy {
    unsafe extern "C" fn alloc(&self, layout: alloc_traits::FfiLayout) -> *mut u8 {
        // SAFETY: caller upholds `GlobalAllocatorV1::alloc`'s contract.
        unsafe { APP_ALLOCATOR.alloc(Layout::from(layout)) }
    }

    unsafe extern "C" fn dealloc(&self, ptr: *mut u8, layout: alloc_traits::FfiLayout) {
        // SAFETY: caller upholds `GlobalAllocatorV1::dealloc`'s contract.
        unsafe { APP_ALLOCATOR.dealloc(ptr, Layout::from(layout)) }
    }

    unsafe extern "C" fn alloc_zeroed(&self, layout: alloc_traits::FfiLayout) -> *mut u8 {
        // SAFETY: caller upholds `GlobalAllocatorV1::alloc_zeroed`'s contract.
        unsafe { APP_ALLOCATOR.alloc_zeroed(Layout::from(layout)) }
    }

    unsafe extern "C" fn realloc(
        &self,
        ptr: *mut u8,
        layout: alloc_traits::FfiLayout,
        new_size: usize,
    ) -> *mut u8 {
        // SAFETY: caller upholds `GlobalAllocatorV1::realloc`'s contract.
        unsafe { APP_ALLOCATOR.realloc(ptr, Layout::from(layout), new_size) }
    }
}
