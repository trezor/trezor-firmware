use crate::{
    common::{confirm_signverify, decode_message},
    helpers::{address_from_bytes, bytes_from_address},
    proto::{common::HdNodeType, common::Success, ethereum::EthereumVerifyMessage},
    sign_message::message_digest,
    strutil::hex_encode,
};
#[cfg(not(test))]
use alloc::{string::ToString, vec::Vec};
#[cfg(test)]
use std::{string::ToString, vec::Vec};
use trezor_app_sdk::{Error, Result, crypto, info, log, ui, util::HdNodeData};

pub fn verify_message(msg: EthereumVerifyMessage) -> Result<Success> {
    let digest = message_digest(msg.message.as_slice());
    if msg.signature.len() != 65 {
        // TODO: DataError("Invalid signature")
        return Err(Error::DataError);
    }

    let signature: [u8; 65] = msg
        .signature
        .as_slice()
        .try_into()
        .map_err(|_| Error::DataError)?;

    let sig = [signature[64]] // recovery id
        .iter()
        .chain(signature[..64].iter())
        .cloned()
        .collect::<Vec<u8>>()
        .try_into()
        .map_err(|_| Error::DataError)?;

    let (pubkey, len) = crypto::secp256k1_verify_recover(&sig, &digest).ok_or(Error::DataError)?;

    let pkh_hash = crypto::keccak_256(&pubkey[1..len]);
    let pkh = &pkh_hash[pkh_hash.len() - 20..]; // Last 20 bytes

    let address_bytes = bytes_from_address(&msg.address)?;

    if address_bytes != pkh {
        // TODO DataError("Invalid signature")
        return Err(Error::DataError);
    }

    let address = address_from_bytes(&address_bytes, None);

    confirm_signverify(
        &decode_message(&msg.message),
        &address,
        true,
        None,
        None,
        false,
    )?;

    Ok(Success::default())
}
