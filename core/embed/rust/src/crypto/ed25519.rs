use super::{ffi, Error};

pub type Signature = ffi::ed25519_signature;
pub const SIGNATURE_SIZE: usize = core::mem::size_of::<Signature>();

pub type PublicKey = ffi::ed25519_public_key;
pub const PUBLIC_KEY_SIZE: usize = core::mem::size_of::<PublicKey>();

mod ffi_override {
    // bindgen incorrectly generates pk and RS as *mut instead of *const
    // https://github.com/rust-lang/rust-bindgen/pull/2684
    extern "C" {
        pub fn ed25519_sign_open(
            m: *const cty::c_uchar,
            mlen: usize,
            pk: *const cty::c_uchar,
            RS: *const cty::c_uchar,
        ) -> cty::c_int;
    }
}

pub fn verify(message: &[u8], public_key: &PublicKey, signature: &Signature) -> Result<(), Error> {
    let res = unsafe {
        ffi_override::ed25519_sign_open(
            message.as_ptr(),
            message.len(),
            public_key.as_ptr(),
            signature.as_ptr(),
        )
    };
    if res == 0 {
        Ok(())
    } else {
        Err(Error::SignatureVerificationFailed)
    }
}
