#![no_std]
#![no_main]

extern crate alloc;

use prost::Message as _;
use trezor_app_sdk::service::{self, CoreIpcService};
use trezor_app_sdk::util::Timeout;
use trezor_app_sdk::{CORE_SERVICE, Error, IpcMessage, Result, error};

// Include generated protobuf code
pub(crate) mod proto;

mod common;

mod get_address;
mod get_public_key;
mod sign_message;
mod sign_tx;
mod sign_typed_data;

use proto::ethereum::{
    EthereumAddress, EthereumGetAddress, EthereumGetPublicKey, EthereumMessageSignature,
    EthereumPublicKey, EthereumSignMessage, EthereumSignTx, EthereumTxRequest,
};
use proto::ethereum_eip712::{EthereumSignTypedData};
use ufmt::derive::uDebug;
use ufmt_utils::WriteAdapter;

#[derive(uDebug, Copy, Clone, PartialEq, Eq, num_enum::FromPrimitive, num_enum::IntoPrimitive)]
#[repr(u16)]
enum EthereumMessages {
    GetPublicKey = 0,
    PublicKey = 1,
    GetAddress = 2,
    Address = 3,
    SignMessage = 4,
    MessageSignature = 5,
    SignTx = 6,
    TxRequest = 7,
    SignTypedData = 8,

    #[num_enum(catch_all)]
    Unknown(u16),
}

#[global_allocator]
static ALLOCATOR: emballoc::Allocator<4096> = emballoc::Allocator::new();

/// Macro to generate handler functions
macro_rules! wire_handler {
    ($handler_name:ident, $request_type:ty, $response_msg:expr, $handler_fn:path) => {
        fn $handler_name(request_data: &[u8]) -> Result<()> {
            let request =
                <$request_type>::decode(request_data).map_err(|_| Error::InvalidMessage)?;

            let response = $handler_fn(request)?;

            let response_bytes = response.encode_to_vec();
            let message = IpcMessage::new($response_msg.into(), &response_bytes);
            message.send(service::CORE_SERVICE_REMOTE, CoreIpcService::WireEnd.into())?;
            Ok(())
        }
    };
}

// Generate all handler functions
wire_handler!(
    handle_get_public_key,
    EthereumGetPublicKey,
    EthereumMessages::PublicKey,
    get_public_key::get_public_key
);
wire_handler!(
    handle_get_address,
    EthereumGetAddress,
    EthereumMessages::Address,
    get_address::get_address
);
wire_handler!(
    handle_sign_message,
    EthereumSignMessage,
    EthereumMessages::MessageSignature,
    sign_message::sign_message
);
wire_handler!(
    handle_sign_tx,
    EthereumSignTx,
    EthereumMessages::TxRequest,
    sign_tx::sign_tx
);
wire_handler!(
    handle_sign_typed_data,
    EthereumSignTypedData,
    EthereumMessages::SignTypedData,
    sign_typed_data::sign_typed_data
);

// Application entry point - receives raw bytes, returns raw bytes
#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    let message = CORE_SERVICE.receive(Timeout::max())?;
    match message.service().into() {
        CoreIpcService::WireStart => handle_wire_message(&message),
        _ => {
            error!(
                "Invalid service invoked: {:?}, message id {:?}, data {:?}",
                message.service(),
                message.id(),
                message.data()
            );
            Err(Error::InvalidFunction)
        }
    }
}

/// Entry point for handling protobuf function calls
/// fn_id: function identifier
/// data: serialized protobuf request
/// Returns: serialized protobuf response
pub fn handle_wire_message(message: &IpcMessage) -> Result<()> {
    match message.id().into() {
        EthereumMessages::GetPublicKey => handle_get_public_key(message.data()),
        EthereumMessages::GetAddress => handle_get_address(message.data()),
        EthereumMessages::SignMessage => handle_sign_message(message.data()),
        EthereumMessages::SignTx => handle_sign_tx(message.data()),
        EthereumMessages::SignTypedData => handle_sign_typed_data(message.data()),
        _ => Err(Error::InvalidFunction),
    }
}
