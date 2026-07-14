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
use trezor_app_sdk::{Error, Result, ResultExt, crypto, ui};

pub fn verify_message(msg: VerifyMessage) -> Result<Success> {
    let digest = message_digest(msg.message.as_slice());

    let mut sig: [u8; 65] = msg
        .signature
        .as_slice()
        .try_into()
        .map_err(|_| Error::DataError("Invalid signature"))?;

    sig.rotate_right(1);

    let pubkey = crypto::secp256k1_verify_recover(&sig, &digest)
        .ok_or(Error::DataError("Invalid signature"))?;

    let mut hasher = crypto::Keccak256::new(Some(&pubkey[1..]));
    let pkh_hash = hasher.digest();

    let address_bytes =
        bytes_from_address(&msg.address).context("Failed to convert address to bytes")?;

    // We can use unwrap here because the hash is always 32 bytes
    if address_bytes
        != pkh_hash
            .last_chunk::<20>()
            .ok_or(Error::DataError("Hash is too short"))?
    {
        return Err(Error::DataError("Invalid signature"));
    }

    let address =
        address_from_bytes(&address_bytes, None).context("Failed to convert bytes to address")?;

    confirm_signverify(
        &decode_message(&msg.message).context("Failed to decode message")?,
        &address,
        true,
        None,
        None,
        false,
    )
    .context("Failed to confirm sign/verify")?;

    ui::show_success(ui::ShowSuccess::new(
        tr!("words__title_done"),
        tr!("ethereum__valid_signature"),
        tr!("buttons__continue"),
        None,
        Some("verify_message"),
        ButtonRequestType::Other.into(),
    ))?;

    let msg = Success {
        message: Some("Message verified".into()),
    };

    Ok(msg)
}
