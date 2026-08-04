#![cfg_attr(not(test), no_std)]
#![cfg_attr(not(test), no_main)]
#![allow(clippy::too_many_arguments)]
#![allow(clippy::type_complexity)]
#![allow(dead_code)]
#![deny(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

#[cfg(not(test))]
extern crate alloc;

use prost::Message;
use trezor_app_sdk::{
    Error, Result, ResultExt, WireDecode, WireEncode, error, wire_handler, wire_receive_wire_start,
    wire_request_type,
};

// Include generated code
pub(crate) mod proto;

#[macro_use]
pub(crate) mod translations;

pub(crate) mod alloc_types;
mod clear_signing;
mod clear_signing_definitions;
mod common;
mod cosi;
mod definitions;
mod get_address;
mod get_public_key;
mod helpers;
mod layout;
mod paths;
mod payment_request;
mod rlp;
mod sc_constants;
mod sign_message;
mod sign_tx;
mod sign_tx_eip1559;
mod sign_typed_data;
mod staking;
mod strutil;
mod tokens;
mod verify_message;
mod yielding;
mod yielding_vaults;

use proto::{
    ethereum::{
        DefinitionAck, DefinitionRequest, GetAddress, GetPublicKey, SignMessage, SignTx,
        SignTxEip1559, SignTypedData, TxAck, TxRequest, TypedDataStructAck, TypedDataStructRequest,
        TypedDataValueAck, TypedDataValueRequest, VerifyMessage,
    },
    messages::MessageType,
};

/// Wire codec for [`wire_handler!`]/[`wire_request`] — encodes/decodes
/// messages via [`prost`].
///
/// This is the only place in the app that ties the SDK's serializer-agnostic
/// wire plumbing to prost; the SDK crate itself has no prost dependency.
struct ProstCodec;

impl<T: Message + Default> WireDecode<T> for ProstCodec {
    fn decode(data: &[u8]) -> Result<T> {
        T::decode(data).map_err(|_| Error::InvalidMessage)
    }
}

impl<T: Message> WireEncode<T> for ProstCodec {
    fn encode(val: &T) -> alloc_types::Vec<u8> {
        val.encode_to_vec()
    }
}

/// Sends a request to core via [`ProstCodec`] and decodes the response.
///
/// The response type and wire id come from `Req`'s `wire_request_type!`
/// declaration below, instead of being repeated at every call site.
fn wire_request<Req>(req: &Req) -> Result<Req::Response>
where
    Req: trezor_app_sdk::WireRequest,
    ProstCodec: WireEncode<Req> + WireDecode<Req::Response>,
{
    trezor_app_sdk::wire_request::<ProstCodec, Req>(req)
}

wire_request_type!(TypedDataStructRequest => TypedDataStructAck, MessageType::TypedDataStructRequest);
wire_request_type!(TypedDataValueRequest => TypedDataValueAck, MessageType::TypedDataValueRequest);
wire_request_type!(DefinitionRequest => DefinitionAck, MessageType::DefinitionRequest);
wire_request_type!(TxRequest => TxAck, MessageType::TxRequest);

// Generate all handler functions
wire_handler!(
    handle_get_public_key,
    ProstCodec,
    GetPublicKey,
    MessageType::PublicKey,
    get_public_key::get_public_key
);
wire_handler!(
    handle_get_address,
    ProstCodec,
    GetAddress,
    MessageType::Address,
    get_address::get_address
);
wire_handler!(
    handle_sign_message,
    ProstCodec,
    SignMessage,
    MessageType::MessageSignature,
    sign_message::sign_message
);
wire_handler!(
    handle_sign_tx,
    ProstCodec,
    SignTx,
    MessageType::TxRequest,
    sign_tx::sign_tx
);
wire_handler!(
    handle_sign_tx_eip1559,
    ProstCodec,
    SignTxEip1559,
    MessageType::TxRequest,
    sign_tx_eip1559::sign_tx_eip1559
);
wire_handler!(
    handle_sign_typed_data,
    ProstCodec,
    SignTypedData,
    MessageType::TypedDataSignature,
    sign_typed_data::sign_typed_data
);
wire_handler!(
    handle_verify_message,
    ProstCodec,
    VerifyMessage,
    MessageType::Success,
    verify_message::verify_message
);

// Application entry point - receives raw bytes, returns raw bytes
#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    loop {
        let (id, data) = wire_receive_wire_start().c()?;
        handle_wire_message(id as i32, &data).c()?;
    }
}

/// Entry point for handling protobuf function calls
/// fn_id: function identifier
/// data: serialized protobuf request
/// Returns: serialized protobuf response
pub fn handle_wire_message(id: i32, data: &[u8]) -> Result<()> {
    match id.try_into() {
        Ok(MessageType::GetPublicKey) => handle_get_public_key(data),
        Ok(MessageType::GetAddress) => handle_get_address(data),
        Ok(MessageType::SignMessage) => handle_sign_message(data),
        Ok(MessageType::SignTx) => handle_sign_tx(data),
        Ok(MessageType::SignTxEip1559) => handle_sign_tx_eip1559(data),
        Ok(MessageType::SignTypedData) => handle_sign_typed_data(data),
        Ok(MessageType::VerifyMessage) => handle_verify_message(data),
        Ok(_) => {
            error!("Invalid function: {:?}", id);
            Err(Error::InvalidFunction)?
        }
        Err(_) => {
            error!("Non existing message type: {:?}", id);
            Err(Error::InvalidFunction)?
        }
    }
}

#[cfg(test)]
pub(crate) mod test_init {
    use std::sync::Once;
    use trezor_app_sdk::mock::{dummy_trezor_api_getter_t, sdk_init};
    pub static INIT: Once = Once::new();

    pub fn init_sdk() {
        INIT.call_once(|| unsafe {
            sdk_init(Some(dummy_trezor_api_getter_t));
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn test_init_sdk() {
        test_init::init_sdk();
    }

    #[test]
    #[cfg(feature = "model_t3w1")]
    fn test_model_t3w1() {
        assert!(cfg!(feature = "model_t3w1"));
        assert!(!cfg!(feature = "model_t3t1"));
    }

    #[test]
    #[cfg(feature = "model_t3t1")]
    fn test_model_t3t1() {
        assert!(cfg!(feature = "model_t3t1"));
        assert!(!cfg!(feature = "model_t3w1"));
    }
}
