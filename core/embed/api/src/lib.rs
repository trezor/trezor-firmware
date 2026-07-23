#![no_std]

use rtl::fatal_error;
use trezor_app_sdk::traits::ApiVariant;

extern crate alloc;

mod allocator;
mod crypto;
mod syslog;
mod v1;

#[unsafe(no_mangle)]
pub extern "C" fn get_api(version: u32) -> ApiVariant {
    if version != 1 {
        fatal_error!("Unsupported API version");
    }
    ApiVariant::V1(&v1::TREZOR_API_V1)
}
