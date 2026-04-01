use crate::{
    common::{confirm_signverify, decode_message},
    helpers::{address_from_bytes, bytes_from_address},
    proto::{
        common::{Success, button_request::ButtonRequestType},
        ethereum::EthereumVerifyMessage,
    },
    sign_message::message_digest,
};
#[cfg(not(test))]
use alloc::{string::ToString, vec::Vec};
#[cfg(test)]
use std::{string::ToString, vec::Vec};
use trezor_app_sdk::{Error, Result, crypto, info, ui};

pub fn verify_message(msg: EthereumVerifyMessage) -> Result<Success> {
    info!("verify message");
    let digest = message_digest(msg.message.as_slice());
    if msg.signature.len() != 65 {
        // TODO: proper error type: DataError("Invalid signature")
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

    info!("verifying secp256k1_verify_recover");
    let (pubkey, len) = crypto::secp256k1_verify_recover(&sig, &digest).ok_or(Error::DataError)?;

    info!("hashing pubkey");
    let pkh_hash = crypto::keccak_256(&pubkey[1..len]);
    let pkh = &pkh_hash[pkh_hash.len() - 20..]; // Last 20 bytes

    info!("getting address");
    let address_bytes = bytes_from_address(&msg.address)?;

    if address_bytes != pkh {
        // TODO: proper error type: DataError("Invalid signature")
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

    ui::show_success(
        "Done",
        "The signature is valid.",
        "Continue",
        None,
        Some("verify_message"),
        ButtonRequestType::ButtonRequestOther.into(),
    )?;

    let mut msg = Success::default();
    msg.message = Some("Message verified".to_string());

    Ok(msg)
}
