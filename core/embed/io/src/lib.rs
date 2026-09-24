#![cfg_attr(not(test), no_std)]
#![no_main]
#![feature(custom_test_frameworks)]
#![reexport_test_harness_main = "test_main"]

mod ffi;

#[cfg(feature = "nrf")]
pub mod nrf;
#[cfg(feature = "smp")]
pub mod smp;

/// Returns the heap pointer/size the loader carved out for the currently
/// active applet, sized per its manifest-declared `heap-size`.
#[cfg(feature = "app_loading")]
pub fn get_heap() -> (*mut u8, usize) {
    let mut ptr: *mut core::ffi::c_void = core::ptr::null_mut();
    let mut size = 0usize;
    // SAFETY: `ptr`/`size` are valid out-pointers for the duration of the call.
    let status = unsafe { ffi::app_get_heap(&mut ptr, &mut size) };
    assert!(status.code == 0, "app_get_heap failed");
    (ptr.cast(), size)
}

#[cfg(test)]
#[unsafe(no_mangle)]
pub fn main() -> i32 {
    unsafe extern "C" {
        safe fn rust_tests_c_setup();
    }

    // Initialize the C part of the library before running any tests
    rust_tests_c_setup();

    // Call the Rust test harness main function
    // The function panics if any test fails.
    // Asserting that it returns () to ensure that if a future Rust version
    // changes the signature and behavior, we'll be notified.
    assert_eq!(test_main(), ());

    // Return 0 to indicate success
    0
}
