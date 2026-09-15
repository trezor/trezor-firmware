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

// The API getter handed to every loaded app, by `coreapp_app_entry` below.
// Exported under a stable symbol name because it is the entry point of
// Core's whole app-facing ABI surface, even though nothing outside this
// crate references it any more.
#[unsafe(no_mangle)]
pub extern "C" fn coreapp_api_get(version: u32) -> ApiVariant {
    if version != 1 {
        fatal_error!("Unsupported API version");
    }
    ApiVariant::V1(&v1::TREZOR_API_V1)
}

// The entry point a newly loaded app's task is started on, instead of the
// app's own `applet_main`. The loader (`core/embed/io/app_arena/*/
// app_loader.c`, via `coreapp_get_app_entry()`) schedules *this* function
// and passes `applet_main` to it, so Core gets to run on the app's task
// before the app does.
//
// The point of the inversion is [`allocator::init`]: the app's
// `#[global_allocator]` forwards every allocation over the API vtable into
// Core's `APP_ALLOCATOR`, so that allocator has to be pointed at this app's
// heap region before the app executes a single instruction. Doing it here
// means an app can allocate from the very first line of `applet_main`,
// rather than only after it has called back into `TrezorApiV1::init`.
//
// Same "C only ever takes its address" contract as `coreapp_api_get` above:
// `core/embed/sys/task/*/coreapp.c` declares this as
// `extern int coreapp_app_entry(void* applet_main)` and never calls it, so
// the declared C parameter type does not need to match the real one below.
#[unsafe(no_mangle)]
pub extern "C" fn coreapp_app_entry(
    applet_main: extern "C" fn(ApiGetter) -> core::ffi::c_int,
) -> core::ffi::c_int {
    allocator::init();
    applet_main(coreapp_api_get)
}
