pub mod allocator;
pub mod crypto;
//pub mod service;
pub mod syslog;
pub mod trezor_v1;
pub mod util;

pub use trezor_v1::{TrezorApiV1, TrezorApiV1Struct};

#[stabby::stabby]
#[repr(C, u8)]
pub enum ApiVariant {
    V1(&'static TrezorApiV1Struct) = 1,
}

pub type ApiGetter = extern "C" fn(version: u32) -> ApiVariant;
