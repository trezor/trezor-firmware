/*/// Implementation of the global allocator. Enables usage of `core::alloc` crate.
use crate::micropython::ffi;
use core::alloc::{GlobalAlloc, Layout};

// TODO: Lift this module to higher level.

pub struct Alloc;

unsafe impl GlobalAlloc for Alloc {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        unsafe {
            let raw = ffi::gc_alloc(layout.size(), 0);
            if raw.is_null() {
                panic!("Allocation failed!");
            }
            raw.cast()
        }
    }

    // Deallocation solved by micropython garbage collector.
    unsafe fn dealloc(&self, _ptr: *mut u8, _layout: Layout) {}
}

#[global_allocator]
static A: Alloc = Alloc;
*/
/*
use core::sync::atomic::AtomicBool;
use core::sync::atomic::Ordering;

static mut ARENA: [[u8; 16]; 4] = [[0u8; 16]; 4];
static FREE: [AtomicBool; 4] = [
    AtomicBool::new(true),
    AtomicBool::new(true),
    AtomicBool::new(true),
    AtomicBool::new(true),
];

unsafe impl GlobalAlloc for Alloc {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if layout.size() != 16 {
            //panic!("alloc: unexpected layout size")
        }
        for i in 0..4 {
            if FREE[i].load(Ordering::Relaxed) {
                FREE[i].store(false, Ordering::Relaxed);
                return unsafe { ARENA[i].as_mut_ptr() };
            }
        }
        panic!("alloc: out of memory");
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        if layout.size() != 16 {
            //panic!("alloc: unexpected layout size")
        }
        for i in 0..4 {
            if unsafe { ARENA[i].as_mut_ptr() } == ptr {
                FREE[i].store(true, Ordering::Relaxed);
                return;
            }
        }
        //panic!("alloc: unknown pointer")
    }
}
*/
