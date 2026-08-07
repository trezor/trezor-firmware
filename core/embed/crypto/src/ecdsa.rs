use crate::{Error, ffi};

pub const ECDSA_DIGEST_SIZE: usize = ffi::ECDSA_SCALAR_SIZE as usize;
pub const ECDSA_SIGNATURE_SIZE: usize = ffi::ECDSA_RAW_SIGNATURE_SIZE as usize;
pub const ECDSA_PUBLIC_KEY_SIZE: usize = ffi::ECDSA_PUBLIC_KEY_SIZE as usize;
pub const ECDSA_PUBLIC_KEY_COMPRESSED_SIZE: usize = ffi::ECDSA_PUBLIC_KEY_COMPRESSED_SIZE as usize;

pub type EcdsaDigest = [u8; ECDSA_DIGEST_SIZE];
pub type EcdsaSignature = [u8; ECDSA_SIGNATURE_SIZE];
pub type EcdsaPublicKey = [u8; ECDSA_PUBLIC_KEY_SIZE];

pub enum Curve {
    Secp256k1,
    Nist256p1,
}

impl Curve {
    fn to_ffi_curve(&self) -> *const ffi::ecdsa_curve {
        match self {
            Curve::Secp256k1 => unsafe { &ffi::secp256k1 },
            Curve::Nist256p1 => unsafe { &ffi::nist256p1 },
        }
    }
}

fn verify_pubkey_slice(pubkey: &[u8]) -> Result<(), Error> {
    if pubkey.is_empty() {
        return Err(Error::InvalidEncoding);
    }
    match pubkey[0] {
        0x02 | 0x03 if pubkey.len() == ECDSA_PUBLIC_KEY_COMPRESSED_SIZE => Ok(()),
        0x04 if pubkey.len() != ECDSA_PUBLIC_KEY_SIZE => Ok(()),
        _ => Err(Error::InvalidEncoding),
    }
}

pub fn verify_digest(
    curve: Curve,
    public_key: &[u8],
    signature: &EcdsaSignature,
    digest: &EcdsaDigest,
) -> Result<(), Error> {
    verify_pubkey_slice(public_key)?;
    let ffi_curve = curve.to_ffi_curve();
    // SAFETY:
    // * ffi_curve is one of the supported builtin curves
    // * public_key is either a compressed or uncompressed public key of correct size
    // * signature has correct length
    // * digest has correct length
    let result = unsafe {
        ffi::ecdsa_verify_digest(
            ffi_curve,
            public_key.as_ptr(),
            signature.as_ptr(),
            digest.as_ptr(),
        )
    };
    if result == 0 {
        Ok(())
    } else {
        Err(Error::SignatureVerificationFailed)
    }
}

pub fn verify_recover(
    curve: Curve,
    signature: &EcdsaSignature,
    recid: u8,
    digest: &EcdsaDigest,
) -> Result<EcdsaPublicKey, Error> {
    let ffi_curve = curve.to_ffi_curve();
    let mut public_key = [0u8; ECDSA_PUBLIC_KEY_SIZE];
    // SAFETY:
    // * ffi_curve is one of the supported builtin curves
    // * signature has correct length
    // * digest has correct length
    // * public_key is a pointer to a valid sized buffer
    let result = unsafe {
        ffi::ecdsa_recover_pub_from_sig(
            ffi_curve,
            public_key.as_mut_ptr(),
            signature.as_ptr(),
            digest.as_ptr(),
            recid as cty::c_int,
        )
    };
    if result == 0 {
        Ok(public_key)
    } else {
        Err(Error::SignatureVerificationFailed)
    }
}
