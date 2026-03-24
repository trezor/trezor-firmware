use crate::{
    common::confirm_signverify,
    definitions::Definitions,
    helpers::address_from_bytes,
    keychain::{Keychain, PATTERNS_ADDRESS, schemas_from_network},
    paths::Bip32Path,
    proto::ethereum::{EthereumMessageSignature, EthereumSignMessage},
    uformat,
};
#[cfg(not(test))]
use alloc::vec::Vec;
#[cfg(test)]
use std::vec::Vec;
use trezor_app_sdk::{Result, crypto};

/// Ethereum uses Bitcoin xpub format
pub fn sign_message(msg: EthereumSignMessage) -> Result<EthereumMessageSignature> {
    let dp = Bip32Path::from_slice(&msg.address_n);

    let slip44 = dp.slip44();
    let definitions = Definitions::from_encoded(
        msg.encoded_network.as_ref().map(|d| d.as_ref()),
        None,
        None,
        slip44,
    )
    .unwrap();

    let schemas = schemas_from_network(&PATTERNS_ADDRESS, definitions.slip44())?;
    let keychain = Keychain::new(schemas);

    dp.validate(&keychain)?;

    let encoded_network = msg.encoded_network.as_ref().map(|buf| buf.as_ref());
    let pubkey_hash = crypto::get_eth_pubkey_hash(dp.as_ref(), encoded_network, None)?;
    let address = address_from_bytes(&pubkey_hash, Some(definitions.network()));
    let path = dp.to_string();

    let account = "ETH";

    let message = crate::common::decode_message(&msg.message);

    confirm_signverify(&message, &address, false, Some(&path), Some(account), false)?;

    let hash = message_digest(&msg.message);

    let encoded_network = msg.encoded_network.as_ref().map(|buf| buf.as_ref());
    let signature = crypto::sign_typed_hash(dp.as_ref(), &hash, encoded_network, None, None)?;

    let mut sig = signature[1..].to_vec();
    sig.push(signature[0]);

    let mut res = EthereumMessageSignature::default();
    res.address = address;
    res.signature = sig;

    Ok(res)
}

pub fn message_digest(message: &[u8]) -> [u8; 32] {
    const SIGNED_MESSAGE_HEADER: &[u8] = b"\x19Ethereum Signed Message:\n";

    // Build the complete message to hash
    let mut data = Vec::new();
    data.extend_from_slice(SIGNED_MESSAGE_HEADER);

    // Add the message length as string
    let len_str = uformat!("{}", message.len());
    data.extend_from_slice(len_str.as_bytes());

    // Add the actual message
    data.extend_from_slice(message);

    // Compute keccak256 hash
    crypto::keccak_256(&data)
}
