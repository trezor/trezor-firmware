#![no_std]
#![no_main]

extern crate alloc;

use prost::Message as _;
use trezor_app_sdk::service::{self, CoreIpcService};
use trezor_app_sdk::util::Timeout;
use trezor_app_sdk::{CORE_SERVICE, Error, IpcMessage, Result, error};

// Include generated protobuf code
pub(crate) mod proto;

mod get_address;
mod get_public_key;
mod sign_message;
mod sign_tx;

use proto::ethereum::{
    EthereumAddress, EthereumGetAddress, EthereumGetPublicKey, EthereumMessageSignature,
    EthereumPublicKey, EthereumSignMessage, EthereumSignTx, EthereumTxRequest,
};
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

    #[num_enum(catch_all)]
    Unknown(u16),
}

#[global_allocator]
static ALLOCATOR: emballoc::Allocator<4096> = emballoc::Allocator::new();

/// Handle GetPublicKey request
fn handle_get_public_key(request_data: &[u8]) -> Result<()> {
    // Deserialize the request
    let request =
        <EthereumGetPublicKey>::decode(request_data).map_err(|_| Error::InvalidMessage)?;

    let response = get_public_key::get_public_key(request)?;

    let response_bytes = response.encode_to_vec();
    let message = IpcMessage::new(EthereumMessages::PublicKey.into(), &response_bytes);
    Ok(message.send(service::CORE_SERVICE_REMOTE, CoreIpcService::WireEnd.into())?)
}

fn handle_get_address(request_data: &[u8]) -> Result<()> {
    // Deserialize the request
    let request = <EthereumGetAddress>::decode(request_data).map_err(|_| Error::InvalidMessage)?;

    let response = get_address::get_address(request)?;

    let response_bytes = response.encode_to_vec();
    let message = IpcMessage::new(EthereumMessages::Address.into(), &response_bytes);
    Ok(message.send(service::CORE_SERVICE_REMOTE, CoreIpcService::WireEnd.into())?)
}

fn handle_sign_message(request_data: &[u8]) -> Result<()> {
    // Deserialize the request
    let request = <EthereumSignMessage>::decode(request_data).map_err(|_| Error::InvalidMessage)?;

    let response = sign_message::sign_message(request)?;

    let response_bytes = response.encode_to_vec();
    let message = IpcMessage::new(EthereumMessages::MessageSignature.into(), &response_bytes);
    Ok(message.send(service::CORE_SERVICE_REMOTE, CoreIpcService::WireEnd.into())?)
}

fn handle_sign_tx(request_data: &[u8]) -> Result<()> {
    // Deserialize the request
    let request = <EthereumSignTx>::decode(request_data).map_err(|_| Error::InvalidMessage)?;

    let response = sign_tx::sign_tx(request)?;

    let response_bytes = response.encode_to_vec();
    let message = IpcMessage::new(EthereumMessages::TxRequest.into(), &response_bytes);
    Ok(message.send(service::CORE_SERVICE_REMOTE, CoreIpcService::WireEnd.into())?)
}

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
        _ => Err(Error::InvalidFunction),
    }
}
