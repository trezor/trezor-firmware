use core::alloc::{GlobalAlloc, Layout};
use core::ptr::null_mut;

use trezor_app_sdk::traits::allocator as alloc_traits;

use crate::app_state;

/// Allocates from the heap of the app running on the current task, through
/// the `Talc` in that app's [`app_state::AppState`]. Fails on a task without
/// an app.
///
/// Also the allocator apps use through the API vtable
/// ([`alloc_traits::GlobalAllocatorV1`]).
pub struct AppAllocator;

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

/// The firmware's `#[global_allocator]` when it loads apps.
///
/// On an app's task, allocates from that app's heap. On any other task (Core's
/// own), forwards to `C`. Memory never moves between the two: the API code on
/// an app's task only ever sees the app's allocations, and Core's task never
/// runs app code.
pub struct TaskAllocator<C> {
    core: C,
}

impl<C> TaskAllocator<C> {
    pub const fn new(core: C) -> Self {
        Self { core }
    }
}

unsafe impl<C: GlobalAlloc> GlobalAlloc for TaskAllocator<C> {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        // SAFETY: caller upholds `GlobalAlloc::alloc`'s contract.
        unsafe {
            if app_state::try_get().is_some() {
                AppAllocator.alloc(layout)
            } else {
                self.core.alloc(layout)
            }
        }
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        // SAFETY: caller upholds `GlobalAlloc::dealloc`'s contract; `ptr` was
        // allocated on this task, so by the same allocator.
        unsafe {
            if app_state::try_get().is_some() {
                AppAllocator.dealloc(ptr, layout)
            } else {
                self.core.dealloc(ptr, layout)
            }
        }
    }

    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        // SAFETY: caller upholds `GlobalAlloc::alloc_zeroed`'s contract.
        unsafe {
            if app_state::try_get().is_some() {
                AppAllocator.alloc_zeroed(layout)
            } else {
                self.core.alloc_zeroed(layout)
            }
        }
    }

    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        // SAFETY: caller upholds `GlobalAlloc::realloc`'s contract; `ptr` was
        // allocated on this task, so by the same allocator.
        unsafe {
            if app_state::try_get().is_some() {
                AppAllocator.realloc(ptr, layout, new_size)
            } else {
                self.core.realloc(ptr, layout, new_size)
            }
        }
    }
}

unsafe impl alloc_traits::GlobalAllocatorV1 for AppAllocator {
    unsafe extern "C" fn alloc(&self, layout: alloc_traits::FfiLayout) -> *mut u8 {
        // SAFETY: caller upholds `GlobalAllocatorV1::alloc`'s contract.
        unsafe { GlobalAlloc::alloc(self, layout.into()) }
    }

    unsafe extern "C" fn dealloc(&self, ptr: *mut u8, layout: alloc_traits::FfiLayout) {
        // SAFETY: caller upholds `GlobalAllocatorV1::dealloc`'s contract.
        unsafe { GlobalAlloc::dealloc(self, ptr, layout.into()) }
    }

    unsafe extern "C" fn alloc_zeroed(&self, layout: alloc_traits::FfiLayout) -> *mut u8 {
        // SAFETY: caller upholds `GlobalAllocatorV1::alloc_zeroed`'s contract.
        unsafe { GlobalAlloc::alloc_zeroed(self, layout.into()) }
    }

    unsafe extern "C" fn realloc(
        &self,
        ptr: *mut u8,
        layout: alloc_traits::FfiLayout,
        new_size: usize,
    ) -> *mut u8 {
        // SAFETY: caller upholds `GlobalAllocatorV1::realloc`'s contract.
        unsafe { GlobalAlloc::realloc(self, ptr, layout.into(), new_size) }
    }
}
