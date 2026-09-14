#![no_std]

use rtl::fatal_error;
use trezor_app_sdk::traits::{ApiGetter, ApiVariant};

extern crate alloc;

mod allocator;
mod crypto;
mod syslog;
mod ui;
mod v1;
mod wire;

// The kernel's C code (core/embed/sys/task/*/coreapp.c) declares this symbol
// as `extern const void* coreapp_api_get(uint32_t version)` and only ever
// takes its address (to hand to the app as its API-getter entry point) —
// it never calls it directly, so the declared C return type does not need
// to match the real one below.
#[unsafe(no_mangle)]
pub extern "C" fn coreapp_api_get(version: u32) -> ApiVariant {
    if version != 1 {
        fatal_error!("Unsupported API version");
    }
    ApiVariant::V1(&v1::TREZOR_API_V1)
}

// The loader (`core/embed/sys/task/*/coreapp.c` via
// `core/embed/io/app_arena/*/app_loader.c`) schedules a call to *this*
// function for a newly loaded app's task, instead of jumping into the app's
// own `applet_main` directly — same "C only ever takes its address" contract
// as `coreapp_api_get` above, just handed the app's entry point as its
// argument instead of the other way around. This lets Core finish its own
// per-launch setup (claiming the app's heap for `APP_ALLOCATOR`) before the
// app gets to run at all, rather than only after it has already started and
// made its first vtable call back into `TrezorApiV1::init`.
#[unsafe(no_mangle)]
pub extern "C" fn coreapp_app_entry(
    applet_main: extern "C" fn(ApiGetter) -> core::ffi::c_int,
) -> core::ffi::c_int {
    allocator::init();
    applet_main(coreapp_api_get)
}
