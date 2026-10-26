//! A test-only app that exposes every SDK crypto function to the host.
//!
//! Each wire request names one function and carries its parameters; the app
//! calls the function and answers with its result, or with the error it
//! returned. Meant for device tests of the crypto API; dev-signed only, and
//! it must never ship.

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
pub(crate) mod proto;

use proto::messages::MessageType;
use proto::testapp::{
    Base58CheckDecode, Base58CheckEncode, Base58Decode, Base58Encode, CheckAddressMac,
    CosiCombinePublicKeys, CosiVerify, EcRecoverPubkey, EcVerifyRecover, EcVerifyRecoverDigest,
    GetAddressMac, GetPublicKey, GetXpub, Hash, Hmac, SignDigest, VerifyNonceCache,
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
    handle_sign_digest,
    ProstCodec,
    SignDigest,
    MessageType::Signature,
    crypto::sign_digest
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
    handle_ec_verify_recover,
    ProstCodec,
    EcVerifyRecover,
    MessageType::PublicKey,
    crypto::ec_verify_recover
);
wire_handler!(
    handle_ec_verify_recover_digest,
    ProstCodec,
    EcVerifyRecoverDigest,
    MessageType::PublicKey,
    crypto::ec_verify_recover_digest
);
wire_handler!(
    handle_ec_recover_pubkey,
    ProstCodec,
    EcRecoverPubkey,
    MessageType::PublicKey,
    crypto::ec_recover_pubkey
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
        Ok(MessageType::SignDigest) => handle_sign_digest(data),
        Ok(MessageType::GetAddressMac) => handle_get_address_mac(data),
        Ok(MessageType::CheckAddressMac) => handle_check_address_mac(data),
        Ok(MessageType::VerifyNonceCache) => handle_verify_nonce_cache(data),
        Ok(MessageType::EcVerifyRecover) => handle_ec_verify_recover(data),
        Ok(MessageType::EcVerifyRecoverDigest) => handle_ec_verify_recover_digest(data),
        Ok(MessageType::EcRecoverPubkey) => handle_ec_recover_pubkey(data),
        Ok(MessageType::CosiVerify) => handle_cosi_verify(data),
        Ok(MessageType::CosiCombinePublicKeys) => handle_cosi_combine_publickeys(data),
        Ok(MessageType::Base58Encode) => handle_base58_encode(data),
        Ok(MessageType::Base58Decode) => handle_base58_decode(data),
        Ok(MessageType::Base58CheckEncode) => handle_base58check_encode(data),
        Ok(MessageType::Base58CheckDecode) => handle_base58check_decode(data),
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
