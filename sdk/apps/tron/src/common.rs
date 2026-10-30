use crate::{
    alloc_types::{String, Vec},
    paths::Bip32Path,
};
use trezor_app_sdk::crypto::{self, CanonicalSig, HasherExt as _, HashingAlgorithm};
use trezor_app_sdk::{Error, Result, ResultExt};

pub const COIN: &str = "Tron";
pub const CURVE: &str = "secp256k1";
pub const SLIP44_ID: u32 = 195;

/// [`crypto::get_public_key`] on Tron's curve.
pub(crate) fn get_public_key(address_n: &[u32], compressed: bool) -> Result<Vec<u8>> {
    crypto::get_public_key(crypto::Curve::Secp256k1, address_n, compressed)
}

/// [`crypto::ecdsa_sign_digest`] on Tron's curve.
pub(crate) fn ecdsa_sign_digest(
    address_n: &[u32],
    digest: &[u8; 32],
    compressed: bool,
    canonical: CanonicalSig,
) -> Result<[u8; 65]> {
    crypto::ecdsa_sign_digest(
        crypto::EcdsaCurve::Secp256k1,
        address_n,
        digest,
        compressed,
        canonical,
    )
}

pub(crate) fn get_pubkey_hash(dp: &Bip32Path) -> Result<[u8; 20]> {
    let public_key = get_public_key(dp.as_slice(), false).c()?;

    let mut hasher = crypto::get_hasher(HashingAlgorithm::Keccak256);
    hasher.update(&public_key[1..]);
    let hash = hasher.finalize();
    Ok(hash[12..].try_into().unwrap())
}

pub(crate) fn get_encoded_address(address_bytes: &[u8]) -> Result<String> {
    let address = bs58::encode(address_bytes).with_check().into_string();

    if address.len() != 34 || !address.starts_with('T') {
        return Err(Error::DataError("Tron: Invalid address"));
    }

    Ok(address)
}
