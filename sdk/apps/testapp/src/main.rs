//! A test-only app that exposes every SDK crypto function and every modui
//! layout to the host.
//!
//! Each wire request names one function or layout and carries its parameters;
//! the app calls it and answers with its result, or with the error it
//! returned. Meant for device tests of the crypto API and for testing the UI
//! by hand on every model; dev-signed only, and it must never ship.

#![cfg_attr(not(test), no_std)]
#![cfg_attr(not(test), no_main)]

#[cfg(not(test))]
extern crate alloc;

use prost::Message;
use trezor_app_sdk::{
    Error, Result, ResultExt, WireDecode, WireEncode, debug, error, wire_handler,
    wire_receive_wire_start,
};

pub(crate) mod alloc_types;
mod crypto;
mod layouts;
pub(crate) mod proto;
mod showcase;

use proto::messages::MessageType;
use proto::testapp::{
    Base58CheckDecode, Base58CheckEncode, Base58Decode, Base58Encode, CheckAddressMac,
    CosiCombinePublicKeys, CosiVerify, Danger, Details, Done, EcdsaRecoverPubkey, EcdsaSignDigest,
    EcdsaVerify, EcdsaVerifyDigest, Ed25519Sign, Ed25519Verify, GetAddressMac, GetPublicKey,
    GetXpub, Hash, Hmac, Review, ShowProgress, Showcase, StreamData, VerifyAddress,
    VerifyNonceCache, VerifyPubkey,
};

/// Wire codec for [`wire_handler!`] — encodes/decodes messages via [`prost`].
pub(crate) struct ProstCodec;

impl<T: Message + Default> WireDecode<T> for ProstCodec {
    fn decode(data: &[u8]) -> Result<T> {
        T::decode(data).map_err(|_| Error::InvalidMessage)
    }
}

impl<T: Message> WireEncode<T> for ProstCodec {
    fn encode(val: &T) -> crate::alloc_types::Vec<u8> {
        val.encode_to_vec()
    }
}

wire_handler!(
    handle_hash,
    ProstCodec,
    Hash,
    MessageType::Digest,
    crypto::hash
);
wire_handler!(
    handle_hmac,
    ProstCodec,
    Hmac,
    MessageType::Digest,
    crypto::hmac
);
wire_handler!(
    handle_get_xpub,
    ProstCodec,
    GetXpub,
    MessageType::Xpub,
    crypto::get_xpub
);
wire_handler!(
    handle_get_public_key,
    ProstCodec,
    GetPublicKey,
    MessageType::PublicKey,
    crypto::get_public_key
);
wire_handler!(
    handle_ecdsa_sign_digest,
    ProstCodec,
    EcdsaSignDigest,
    MessageType::Signature,
    crypto::ecdsa_sign_digest
);
wire_handler!(
    handle_ed25519_sign,
    ProstCodec,
    Ed25519Sign,
    MessageType::Signature,
    crypto::ed25519_sign
);
wire_handler!(
    handle_get_address_mac,
    ProstCodec,
    GetAddressMac,
    MessageType::AddressMac,
    crypto::get_address_mac
);
wire_handler!(
    handle_check_address_mac,
    ProstCodec,
    CheckAddressMac,
    MessageType::Success,
    crypto::check_address_mac
);
wire_handler!(
    handle_verify_nonce_cache,
    ProstCodec,
    VerifyNonceCache,
    MessageType::Bool,
    crypto::verify_nonce_cache
);
wire_handler!(
    handle_ecdsa_verify,
    ProstCodec,
    EcdsaVerify,
    MessageType::Success,
    crypto::ecdsa_verify
);
wire_handler!(
    handle_ecdsa_verify_digest,
    ProstCodec,
    EcdsaVerifyDigest,
    MessageType::Success,
    crypto::ecdsa_verify_digest
);
wire_handler!(
    handle_ecdsa_recover_pubkey,
    ProstCodec,
    EcdsaRecoverPubkey,
    MessageType::PublicKey,
    crypto::ecdsa_recover_pubkey
);
wire_handler!(
    handle_ed25519_verify,
    ProstCodec,
    Ed25519Verify,
    MessageType::Success,
    crypto::ed25519_verify
);
wire_handler!(
    handle_cosi_verify,
    ProstCodec,
    CosiVerify,
    MessageType::Success,
    crypto::cosi_verify
);
wire_handler!(
    handle_cosi_combine_publickeys,
    ProstCodec,
    CosiCombinePublicKeys,
    MessageType::PublicKey,
    crypto::cosi_combine_publickeys
);
wire_handler!(
    handle_base58_encode,
    ProstCodec,
    Base58Encode,
    MessageType::Base58,
    crypto::base58_encode
);
wire_handler!(
    handle_base58_decode,
    ProstCodec,
    Base58Decode,
    MessageType::Data,
    crypto::base58_decode
);
wire_handler!(
    handle_base58check_encode,
    ProstCodec,
    Base58CheckEncode,
    MessageType::Base58,
    crypto::base58check_encode
);
wire_handler!(
    handle_base58check_decode,
    ProstCodec,
    Base58CheckDecode,
    MessageType::Data,
    crypto::base58check_decode
);
wire_handler!(
    handle_review,
    ProstCodec,
    Review,
    MessageType::UiResult,
    layouts::review
);
wire_handler!(
    handle_danger,
    ProstCodec,
    Danger,
    MessageType::UiResult,
    layouts::danger
);
wire_handler!(
    handle_details,
    ProstCodec,
    Details,
    MessageType::UiResult,
    layouts::details
);
wire_handler!(
    handle_verify_address,
    ProstCodec,
    VerifyAddress,
    MessageType::UiResult,
    layouts::verify_address
);
wire_handler!(
    handle_verify_pubkey,
    ProstCodec,
    VerifyPubkey,
    MessageType::UiResult,
    layouts::verify_pubkey
);
wire_handler!(
    handle_done,
    ProstCodec,
    Done,
    MessageType::UiResult,
    layouts::done
);
wire_handler!(
    handle_show_progress,
    ProstCodec,
    ShowProgress,
    MessageType::UiResult,
    layouts::show_progress
);
wire_handler!(
    handle_stream_data,
    ProstCodec,
    StreamData,
    MessageType::UiResult,
    layouts::stream_data
);
wire_handler!(
    handle_showcase,
    ProstCodec,
    Showcase,
    MessageType::UiResult,
    showcase::show
);

#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    loop {
        debug!("Waiting for wire message");
        let (id, data) = wire_receive_wire_start().c()?;
        handle_wire_message(id as i32, &data).c()?;
    }
}

/// Dispatches one wire request to its handler.
pub fn handle_wire_message(id: i32, data: &[u8]) -> Result<()> {
    match id.try_into() {
        Ok(MessageType::Hash) => handle_hash(data),
        Ok(MessageType::Hmac) => handle_hmac(data),
        Ok(MessageType::GetXpub) => handle_get_xpub(data),
        Ok(MessageType::GetPublicKey) => handle_get_public_key(data),
        Ok(MessageType::EcdsaSignDigest) => handle_ecdsa_sign_digest(data),
        Ok(MessageType::Ed25519Sign) => handle_ed25519_sign(data),
        Ok(MessageType::GetAddressMac) => handle_get_address_mac(data),
        Ok(MessageType::CheckAddressMac) => handle_check_address_mac(data),
        Ok(MessageType::VerifyNonceCache) => handle_verify_nonce_cache(data),
        Ok(MessageType::EcdsaVerify) => handle_ecdsa_verify(data),
        Ok(MessageType::EcdsaVerifyDigest) => handle_ecdsa_verify_digest(data),
        Ok(MessageType::EcdsaRecoverPubkey) => handle_ecdsa_recover_pubkey(data),
        Ok(MessageType::Ed25519Verify) => handle_ed25519_verify(data),
        Ok(MessageType::CosiVerify) => handle_cosi_verify(data),
        Ok(MessageType::CosiCombinePublicKeys) => handle_cosi_combine_publickeys(data),
        Ok(MessageType::Base58Encode) => handle_base58_encode(data),
        Ok(MessageType::Base58Decode) => handle_base58_decode(data),
        Ok(MessageType::Base58CheckEncode) => handle_base58check_encode(data),
        Ok(MessageType::Base58CheckDecode) => handle_base58check_decode(data),
        Ok(MessageType::Review) => handle_review(data),
        Ok(MessageType::Danger) => handle_danger(data),
        Ok(MessageType::Details) => handle_details(data),
        Ok(MessageType::VerifyAddress) => handle_verify_address(data),
        Ok(MessageType::VerifyPubkey) => handle_verify_pubkey(data),
        Ok(MessageType::Done) => handle_done(data),
        Ok(MessageType::ShowProgress) => handle_show_progress(data),
        Ok(MessageType::StreamData) => handle_stream_data(data),
        Ok(MessageType::Showcase) => handle_showcase(data),
        Ok(_) => {
            error!("Invalid function: {:?}", id);
            Err(Error::InvalidFunction)
        }
        Err(_) => {
            error!("Non existing message type: {:?}", id);
            Err(Error::InvalidFunction)
        }
    }
}
