#![cfg_attr(not(test), no_std)]

#[macro_use]
mod error_util;

pub mod aesgcm;
pub mod cosi;
pub mod crc32;
pub mod curve25519;
pub mod ed25519;
mod ffi;
pub mod hmac;
mod memory;
pub mod merkle;
pub mod sha256;
pub mod sha512;

#[cfg_attr(any(test, feature = "test"), derive(core::fmt::Debug))]
pub enum Error {
    // Signature verification failed
    SignatureVerificationFailed,
    // Provided value is not a valid public key / signature / etc.
    InvalidEncoding,
    // Provided parameters are not accepted (e.g., signature threshold out of bounds)
    InvalidParams,
    // State precondition check failed (possibly raised by C implementation)
    InvalidContext,
}
