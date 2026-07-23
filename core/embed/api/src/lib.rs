#![no_std]

use rtl::fatal_error;
use trezor_app_sdk::traits::ApiVariant;

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
