use core::alloc::{GlobalAlloc as _, Layout};

use trezor_app_sdk::traits::allocator as alloc_traits;

#[global_allocator]
static GLOBAL_ALLOCATOR: talc::TalcLock<spin::Mutex<()>, talc::source::Manual> =
    talc::TalcLock::new(talc::source::Manual);

pub struct AllocatorProxy;

unsafe impl alloc_traits::GlobalAllocatorV1 for AllocatorProxy {
    unsafe extern "C" fn alloc(&self, layout: alloc_traits::FfiLayout) -> *mut u8 {
        let layout = Layout::from(layout);
        unsafe { GLOBAL_ALLOCATOR.alloc(layout) }
    }

    unsafe extern "C" fn dealloc(&self, ptr: *mut u8, layout: alloc_traits::FfiLayout) {
        let layout = Layout::from(layout);
        unsafe { GLOBAL_ALLOCATOR.dealloc(ptr, layout) }
    }

    unsafe extern "C" fn alloc_zeroed(&self, layout: alloc_traits::FfiLayout) -> *mut u8 {
        let layout = Layout::from(layout);
        unsafe { GLOBAL_ALLOCATOR.alloc_zeroed(layout) }
    }

    unsafe extern "C" fn realloc(
        &self,
        ptr: *mut u8,
        layout: alloc_traits::FfiLayout,
        new_size: usize,
    ) -> *mut u8 {
        let layout = Layout::from(layout);
        unsafe { GLOBAL_ALLOCATOR.realloc(ptr, layout, new_size) }
    }
}
