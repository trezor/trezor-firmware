extern crate alloc;

use alloc::vec::{self, Vec};
use trezor_app_sdk::{
    Error, Result,
    crypto::{ed25519_cosi_combine_publickeys, ed25519_sign_open},
};

pub fn select_keys<'a>(sigmask: u8, keys: &'a [&[u8; 32]]) -> Result<Vec<&'a [u8; 32]>> {
    let mut selected_keys = Vec::new();
    let mut sigmask = sigmask;
    for key in keys {
        if sigmask & 1 != 0 {
            selected_keys.push(*key);
        }
        sigmask >>= 1;
    }
    if sigmask != 0 {
        return Err(Error::DataError); // sigmask specifies more public keys than provided
    }
    Ok(selected_keys)
}

pub fn verify(
    signature: &[u8; 64],
    data: &[u8],
    threshold: usize,
    keys: &[&[u8; 32]],
    sigmask: u8,
) -> Result<bool> {
    if threshold < 1 {
        // at least one signer is required
        return Err(Error::DataError);
    }

    let selected_keys = select_keys(sigmask, keys)?;
    if selected_keys.len() < threshold {
        return Ok(false); // insufficient number of signatures
    }

    let global_pk = ed25519_cosi_combine_publickeys(&selected_keys)?;
    Ok(ed25519_sign_open(&global_pk, signature, data)?)
}
