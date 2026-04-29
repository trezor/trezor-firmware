use heapless::Vec;

use super::{ed25519, ffi, Error};

const MAX_PUBKEYS: usize = 3;

pub struct Signature {
    sigmask: u8,
    signature: ed25519::Signature,
}

impl Signature {
    pub fn new(sigmask: u8, signature: ed25519::Signature) -> Self {
        Self { sigmask, signature }
    }
}

pub fn verify(
    threshold: u8,
    message: &[u8],
    public_keys: &[ed25519::PublicKey],
    signature: &Signature,
) -> Result<(), Error> {
    if threshold < 1 {
        return Err(Error::InvalidParams);
    }
    let selected_keys = select_keys(signature.sigmask, public_keys)?;
    if selected_keys.len() < threshold as usize {
        return Err(Error::InvalidParams);
    }
    let combined_key = combine_publickeys(&selected_keys)?;
    ed25519::verify(message, &combined_key, &signature.signature)
}

fn select_keys(
    mut sigmask: u8,
    keys: &[ed25519::PublicKey],
) -> Result<Vec<ed25519::PublicKey, MAX_PUBKEYS>, Error> {
    let mut selected_keys = Vec::new();
    for key in keys {
        if sigmask & 1 != 0 {
            unwrap!(selected_keys.push(*key));
        }
        sigmask >>= 1;
    }
    if sigmask != 0 {
        Err(Error::InvalidParams)
    } else {
        Ok(selected_keys)
    }
}

fn combine_publickeys(keys: &[ed25519::PublicKey]) -> Result<ed25519::PublicKey, Error> {
    let mut combined_key = ed25519::PublicKey::default();
    let res = unsafe {
        ffi::ed25519_cosi_combine_publickeys(&mut combined_key as *mut _, keys.as_ptr(), keys.len())
    };
    if res == 0 {
        Ok(combined_key)
    } else {
        Err(Error::InvalidEncoding)
    }
}
