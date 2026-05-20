use crate::{
    common::decode_message,
    helpers::{address_from_bytes, bytes_from_address},
    layout::confirm_signverify,
    proto::{
        common::{Success, button_request::ButtonRequestType},
        ethereum::VerifyMessage,
    },
    sign_message::message_digest,
};
use trezor_app_sdk::{Error, Result, crypto, ui, unwrap};

pub fn verify_message(msg: VerifyMessage) -> Result<Success> {
    let digest = message_digest(msg.message.as_slice());

    let mut sig: [u8; 65] = msg
        .signature
        .as_slice()
        .try_into()
        .map_err(|_| Error::DataError("Invalid signature"))?;

    sig.rotate_right(1);

    let (pubkey, len) = crypto::secp256k1_verify_recover(&sig, &digest)
        .ok_or(Error::DataError("Invalid signature"))?;

    let mut hasher = crypto::Keccak256::new(Some(&pubkey[1..len]));
    let pkh_hash = hasher.digest();

    let address_bytes = bytes_from_address(&msg.address)?;

    if address_bytes != unwrap!(pkh_hash.last_chunk::<20>()) {
        return Err(Error::DataError("Invalid signature"));
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
        tr!("words__title_done"),
        tr!("ethereum__valid_signature"),
        tr!("buttons__continue"),
        None,
        Some("verify_message"),
        ButtonRequestType::Other.into(),
    )?;

    let msg = Success {
        message: Some("Message verified".into()),
    };

    Ok(msg)
}
