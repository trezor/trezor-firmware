#![cfg_attr(not(test), no_std)]
#![cfg_attr(not(test), no_main)]
// #![reexport_test_harness_main = "test_main"]

#[cfg(not(test))]
extern crate alloc;

// #[cfg(test)]
// extern crate std;

use prost::Message;
use trezor_app_sdk::{
    CORE_SERVICE, Error, IpcMessage, Result, error,
    service::{self, CoreIpcService, NoUtilHandler},
    trace,
    unwrap,
    util::Timeout,
};
// Include generated code
pub(crate) mod proto;

#[macro_use]
pub(crate) mod translations;

mod common;
mod definitions;
mod ed25519;
mod get_address;
mod get_public_key;
mod helpers;
mod keychain;
mod paths;
mod payment_request;
mod rlp;
mod sign_message;
mod sign_tx;
mod sign_tx_eip1559;
mod sign_typed_data;
mod strutil;
mod tokens;
mod verify_message;

use proto::{
    ethereum::{
        GetAddress, GetPublicKey, SignMessage, SignTx, SignTxEip1559, SignTypedData, VerifyMessage,
    },
    messages::MessageType,
};

// TODO: decrease size and use long string confirmation instead of blob
#[cfg(not(test))]
#[global_allocator]
static ALLOCATOR: emballoc::Allocator<65536> = emballoc::Allocator::new();

/// Macro to generate handler functions
macro_rules! wire_handler {
    ($handler_name:ident, $request_type:ty, $response_msg:expr, $handler_fn:path) => {
        fn $handler_name(request_data: &[u8]) -> Result<()> {
            let request =
                <$request_type>::decode(request_data).map_err(|_| Error::InvalidMessage)?;

            let response = $handler_fn(request);

            match response {
                Ok(resp) => {
                    let response_bytes = resp.encode_to_vec();
                    let message = IpcMessage::new(
                        ($response_msg as i32)
                            .try_into()
                            .map_err(|_| Error::InvalidMessage)?,
                        &response_bytes,
                    );
                    message.send(service::CORE_SERVICE_REMOTE, CoreIpcService::WireEnd.into())?;
                }
                Err(e) => {
                    let message = IpcMessage::new(
                        e.code(),
                        e.message().as_bytes(),
                    );
                    message.send(
                        service::CORE_SERVICE_REMOTE,
                        CoreIpcService::WireError.into(),
                    )?;
                }
            }

            Ok(())
        }
    };
}

pub(crate) fn wire_request<Req, Resp>(req: &Req, id: MessageType) -> Result<Resp>
where
    Req: Message,
    Resp: Message + Default,
{
    let req_bytes = req.encode_to_vec();
    let message = IpcMessage::new(unwrap!((id as u32).try_into()), &req_bytes);
    let result = CORE_SERVICE.call(
        CoreIpcService::WireContinue,
        &message,
        Timeout::max(),
        &NoUtilHandler,
    )?;
    Resp::decode(result.data()).map_err(|_| Error::InvalidMessage)
}

// Generate all handler functions
wire_handler!(
    handle_get_public_key,
    GetPublicKey,
    MessageType::PublicKey,
    get_public_key::get_public_key
);
wire_handler!(
    handle_get_address,
    GetAddress,
    MessageType::Address,
    get_address::get_address
);
wire_handler!(
    handle_sign_message,
    SignMessage,
    MessageType::MessageSignature,
    sign_message::sign_message
);
wire_handler!(
    handle_sign_tx,
    SignTx,
    MessageType::TxRequest,
    sign_tx::sign_tx
);
wire_handler!(
    handle_sign_tx_eip1559,
    SignTxEip1559,
    MessageType::TxRequest,
    sign_tx_eip1559::sign_tx_eip1559
);
wire_handler!(
    handle_sign_typed_data,
    SignTypedData,
    MessageType::TypedDataSignature,
    sign_typed_data::sign_typed_data
);
wire_handler!(
    handle_verify_message,
    VerifyMessage,
    MessageType::Success,
    verify_message::verify_message
);

// Application entry point - receives raw bytes, returns raw bytes
#[cfg(not(test))]
#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    loop {
        let message = CORE_SERVICE.receive(Timeout::max())?;
        match message.service().into() {
            CoreIpcService::WireStart => handle_wire_message(&message)?,
            _ => {
                error!(
                    "Invalid service invoked: {:?}, message id {:?}, data {:?}",
                    message.service(),
                    message.id(),
                    message.data()
                );
                return Err(Error::InvalidFunction);
            }
        };
    }
}

/// Entry point for handling protobuf function calls
/// fn_id: function identifier
/// data: serialized protobuf request
/// Returns: serialized protobuf response
pub fn handle_wire_message(message: &IpcMessage) -> Result<()> {
    match (message.id() as i32).try_into() {
        Ok(MessageType::GetPublicKey) => handle_get_public_key(message.data()),
        Ok(MessageType::GetAddress) => handle_get_address(message.data()),
        Ok(MessageType::SignMessage) => handle_sign_message(message.data()),
        Ok(MessageType::SignTx) => handle_sign_tx(message.data()),
        Ok(MessageType::SignTxEip1559) => handle_sign_tx_eip1559(message.data()),
        Ok(MessageType::SignTypedData) => handle_sign_typed_data(message.data()),
        Ok(MessageType::VerifyMessage) => handle_verify_message(message.data()),
        Ok(_) => {
            error!("Invalid function: {:?}", message.id());
            Err(Error::InvalidFunction)
        }
        Err(_) => {
            error!("Non existing message type: {:?}", message.id());
            Err(Error::InvalidFunction)
        }
    }
}
