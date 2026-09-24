#![no_std]
#![no_main]

use sys as _;
use trezor_lib as _;
#[cfg(feature = "tracked_allocator")]
use trezor_lib::TrackedAllocator;

// Apps allocate from their own heaps, Core from MicroPython's tracked
// allocator (`app_loading` implies `tracked_allocator`).
#[cfg(feature = "app_loading")]
#[global_allocator]
static ALLOCATOR: api::allocator::TaskAllocator<TrackedAllocator> =
    api::allocator::TaskAllocator::new(TrackedAllocator);

#[cfg(all(feature = "tracked_allocator", not(feature = "app_loading")))]
#[global_allocator]
static ALLOCATOR: TrackedAllocator = TrackedAllocator;
