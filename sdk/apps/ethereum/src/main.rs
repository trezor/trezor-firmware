#![no_std]
#![no_main]

extern crate alloc;

use alloc::string::String;
use alloc::vec;
use prost::Message as _;
use trezor_app_sdk::service::{self, CoreIpcService};
use trezor_app_sdk::util::Timeout;
use trezor_app_sdk::{error, info, ui, Error, IpcMessage, Result, CORE_SERVICE};

// Include generated protobuf code
mod paths;
mod proto;

use proto::common::HdNodeType;
use proto::ethereum::{EthereumGetPublicKey, EthereumPublicKey};
use ufmt::derive::uDebug;
use ufmt_utils::WriteAdapter;

#[derive(uDebug, Copy, Clone, PartialEq, Eq, num_enum::FromPrimitive, num_enum::IntoPrimitive)]
#[repr(u16)]
enum EthereumMessages {
    GetPublicKey = 0,
    PublicKey = 1,
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

    // TODO: we use the Bitcoin format for Ethereum xpubs
    // - Derive the key from the BIP-32 path using keychain
    // - Generate the xpub from the derived node
    // - Show on display if requested (show_display = true)

    // For now, create a dummy response with required fields
    let mut response = EthereumPublicKey::default();

    // Set required node field
    response.node = HdNodeType::default();

    // Set required xpub field - format: xpub with path info for now

    response.xpub = String::from("xpub661MyMwAqRbcF");

    let response_bytes = response.encode_to_vec();
    let message = IpcMessage::new(EthereumMessages::PublicKey.into(), &response_bytes);
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
        _ => Err(Error::InvalidFunction),
    }
}
