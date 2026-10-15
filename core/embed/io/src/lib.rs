#![cfg_attr(not(test), no_std)]
#![no_main]
#![feature(custom_test_frameworks)]
#![reexport_test_harness_main = "test_main"]

mod ffi;

#[cfg(feature = "nrf")]
pub mod nrf;
#[cfg(feature = "smp")]
pub mod smp;

/// Returns the heap the loader set aside for the currently active applet.
///
/// Its length is what the loader reserved, which can differ from the heap size
/// the app asked for: rounded up to the MPU alignment on hardware, and the
/// app's whole data area on the emulator.
///
/// Every call returns the same region, so it must have exactly one owner,
/// e.g. the allocator the app's heap is handed to once at launch. Turning the
/// result into a `&mut [u8]` more than once, or while that owner uses it,
/// creates aliasing mutable references, which is undefined behavior. This
/// binding has no state of its own to enforce a single owner, which is why it
/// returns a raw slice rather than a reference.
#[cfg(feature = "app_loading")]
pub fn get_heap() -> *mut [u8] {
    let mut ptr: *mut core::ffi::c_void = core::ptr::null_mut();
    let mut size = 0usize;
    // SAFETY: `ptr`/`size` are valid out-pointers for the duration of the call.
    let status = unsafe { ffi::app_get_heap(&mut ptr, &mut size) };
    assert!(status.code == 0, "app_get_heap failed");
    core::ptr::slice_from_raw_parts_mut(ptr.cast(), size)
}

/// Returns the IPC inbox size, in bytes, the currently active applet declared
/// in its manifest (`ipc-buffer-size` under `[package.metadata.trezor]`).
///
/// Validated on the way in: the app header is rejected at load unless this is
/// a power of two in `8..=IPC_MAX_BUFFER_SIZE` that fits inside the app's
/// heap, so callers can size an allocation from it directly.
#[cfg(feature = "app_loading")]
pub fn get_ipc_buffer_size() -> usize {
    let mut size = 0usize;
    // SAFETY: `size` is a valid out-pointer for the duration of the call.
    let status = unsafe { ffi::app_get_ipc_buffer_size(&mut size) };
    assert!(status.code == 0, "app_get_ipc_buffer_size failed");
    size
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
