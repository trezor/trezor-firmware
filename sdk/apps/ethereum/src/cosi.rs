use crate::alloc_types::Vec;
use trezor_app_sdk::{Error, Result, crypto};

pub fn verify(
    signature: &[u8; 64],
    data: &[u8],
    threshold: usize,
    keys: &[&[u8; 32]],
    sigmask: u8,
) -> Result<bool> {
    if threshold < 1 {
        return Err(Error::DataError("At least one signer is required"));
    }

    let keys: Vec<[u8; 32]> = keys.iter().map(|k| **k).collect();
    let threshold: u8 = threshold
        .try_into()
        .map_err(|_| Error::DataError("Threshold too large"))?;

    match crypto::cosi_verify(threshold, data, &keys, sigmask, signature) {
        Ok(()) => Ok(true),
        Err(_) => Ok(false),
    }
}
