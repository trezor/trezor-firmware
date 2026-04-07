use super::{ffi, Error};

pub type Signature = ffi::ed25519_signature;
pub const SIGNATURE_SIZE: usize = core::mem::size_of::<Signature>();

pub type PublicKey = ffi::ed25519_public_key;
pub const PUBLIC_KEY_SIZE: usize = core::mem::size_of::<PublicKey>();

pub fn verify(message: &[u8], public_key: &PublicKey, signature: &Signature) -> Result<(), Error> {
    let res = unsafe {
        ffi::ed25519_sign_open(
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
