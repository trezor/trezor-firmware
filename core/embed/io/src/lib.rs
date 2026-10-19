#![cfg_attr(not(test), no_std)]
#![no_main]
#![feature(custom_test_frameworks)]
#![reexport_test_harness_main = "test_main"]

mod ffi;

#[cfg(feature = "nrf")]
pub mod nrf;
#[cfg(feature = "smp")]
pub mod smp;

/// Launch arguments the loader hands to a loaded app's entry point
/// (`coreapp_app_entry`), copied onto the app's own stack.
///
/// - `applet_main`: the app's own entry point, which `coreapp_app_entry` calls
///   once the app's runtime is set up.
/// - `heap_ptr`/`heap_size`: the heap the loader set aside for the app. Its
///   size is what the loader reserved, which can differ from the heap size the
///   app asked for: rounded up to the MPU alignment on hardware, and the rest
///   of the app's data area on the emulator.
/// - `ipc_buffer_size`: the IPC inbox size, in bytes, the app declared in its
///   manifest (`ipc-buffer-size` under `[package.metadata.trezor]`). Validated
///   on the way in: the app header is rejected at load unless this is a power
///   of two in `8..=IPC_MAX_BUFFER_SIZE` that fits inside the app's heap, so
///   callers can size an allocation from it directly.
#[cfg(feature = "app_loading")]
pub use ffi::app_args_t as AppArgs;

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
