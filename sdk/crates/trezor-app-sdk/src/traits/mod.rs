/// Heap allocation provided by Core.
pub mod allocator;
/// Cryptography: key derivation, signing, hashing and encodings.
pub mod crypto;
/// Logging to Core's system log.
pub mod syslog;
/// The root interface that bundles all the others.
pub mod trezor_v1;
pub mod ui;
/// Result types shared by the other interfaces.
pub mod util;
/// Messaging with the host.
pub mod wire;

pub use trezor_v1::{TrezorApiV1, TrezorApiV1Struct};

/// The API Core hands to an app, by version.
#[stabby::stabby]
#[repr(C, u8)]
pub enum ApiVariant {
    /// Version 1 of the API.
    V1(&'static TrezorApiV1Struct) = 1,
}

/// Function Core passes to `applet_main` to get the API of a given version.
pub type ApiGetter = extern "C" fn(version: u32) -> ApiVariant;
