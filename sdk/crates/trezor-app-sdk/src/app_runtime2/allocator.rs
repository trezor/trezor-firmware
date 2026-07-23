use core::alloc::{GlobalAlloc, Layout};

use crate::traits::allocator::{GlobalAllocatorV1Ref, GlobalAllocatorV1Dyn as _};

#[global_allocator]
static REMOTE_ALLOCATOR: RedirAllocator = RedirAllocator;

pub struct RedirAllocator;

impl RedirAllocator {
    fn allocator(&self) -> GlobalAllocatorV1Ref {
        super::get_api_or_die().allocator
    }
}

unsafe impl GlobalAlloc for RedirAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let remote = self.allocator();
        unsafe { remote.alloc(layout.into()) }
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        let remote = self.allocator();
        unsafe { remote.dealloc(ptr, layout.into()) }
    }

    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        let remote = self.allocator();
        unsafe { remote.alloc_zeroed(layout.into()) }
    }

    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        let remote = self.allocator();
        unsafe { remote.realloc(ptr, layout.into(), new_size) }
    }
}
