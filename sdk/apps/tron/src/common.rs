use crate::{alloc_types::String, paths::Bip32Path};
use trezor_app_sdk::{
    Error, Result, ResultExt,
    crypto::{self, Hasher},
};

pub const COIN: &str = "Tron";
pub const CURVE: &str = "secp256k1";
pub const SLIP44_ID: u32 = 195;

pub(crate) fn get_pubkey_hash(dp: &Bip32Path) -> Result<[u8; 20]> {
    let public_key = crypto::get_public_key(dp.as_slice(), false).c()?;

    let mut hasher = crypto::sha3::Keccak256::new(None);
    hasher.update(&public_key[1..]);
    let mut hash = [0u8; 32];
    hasher.finalize(&mut hash);
    Ok(hash[12..].try_into().unwrap())
}

pub(crate) fn get_encoded_address(address_bytes: &[u8]) -> Result<String> {
    let address = bs58::encode(address_bytes).with_check().into_string();

    if address.len() != 34 || !address.starts_with('T') {
        return Err(Error::DataError("Tron: Invalid address"));
    }

    Ok(address)
}
