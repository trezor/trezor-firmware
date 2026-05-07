use crate::{
    common::COIN,
    definitions::Definitions,
    helpers::address_from_bytes,
    layout::confirm_signverify,
    paths::Bip32Path,
    proto::ethereum::{MessageSignature, SignMessage},
    uformat,
};
use trezor_app_sdk::{
    Result,
    crypto::{self, Hasher},
};

/// Ethereum uses Bitcoin xpub format
pub fn sign_message(msg: SignMessage) -> Result<MessageSignature> {
    let dp = Bip32Path::from_slice(&msg.address_n);

    let encoded_network = msg.encoded_network.as_deref();
    let slip44 = dp.slip44();
    let definitions = Definitions::from_encoded(encoded_network, None, None, slip44)?;

    crypto::verify_derivation_path(dp.as_slice(), encoded_network, None, None)?;

    let encoded_network = msg.encoded_network.as_ref().map(|buf| buf.as_ref());
    let pubkey_hash = crypto::get_eth_pubkey_hash(dp.as_ref(), encoded_network, None)?;
    let address = address_from_bytes(&pubkey_hash, Some(definitions.network()));
    let path = dp.to_string();

    let message = crate::common::decode_message(&msg.message);

    confirm_signverify(&message, &address, false, Some(&path), Some(COIN), false)?;

    let hash = message_digest(&msg.message);

    let encoded_network = msg.encoded_network.as_ref().map(|buf| buf.as_ref());
    let mut signature = crypto::sign_typed_hash(dp.as_ref(), &hash, encoded_network, None, None)?;
    signature.rotate_left(1);

    let mut res = MessageSignature::default();
    res.address = address;
    res.signature = signature.into();

    Ok(res)
}

pub fn message_digest(message: &[u8]) -> [u8; 32] {
    const SIGNED_MESSAGE_HEADER: &[u8] = b"\x19Ethereum Signed Message:\n";

    // Build the complete message to hash
    let mut hasher = crypto::Keccak256::new(Some(SIGNED_MESSAGE_HEADER));

    // Add the message length as string
    let len_str = uformat!("{}", message.len());
    hasher.update(len_str.as_bytes());

    // Add the actual message
    hasher.update(message);

    // Compute keccak256 hash
    hasher.digest()
}
