#![no_std]
#![no_main]

extern crate alloc;

use alloc::string::String;
use alloc::vec;
use prost::Message as _;
use trezor_app_sdk::service::{self, CoreIpcService};
use trezor_app_sdk::util::Timeout;
use trezor_app_sdk::{CORE_SERVICE, Error, IpcMessage, Result, error, info, ui};

// Include generated protobuf code
mod funnycoin_proto {
    include!(concat!(env!("OUT_DIR"), "/funnycoin.rs"));
}
use funnycoin_proto::{FunnycoinGetPublicKey, FunnycoinPublicKey};
use ufmt::derive::uDebug;
use ufmt_utils::WriteAdapter;

#[derive(uDebug, Copy, Clone, PartialEq, Eq, num_enum::FromPrimitive, num_enum::IntoPrimitive)]
#[repr(u16)]
enum FunnycoinMessages {
    GetPublicKey = 0,
    PublicKey = 1,
    #[num_enum(catch_all)]
    Unknown(u16),
}

#[global_allocator]
static ALLOCATOR: emballoc::Allocator<4096> = emballoc::Allocator::new();

// // Provide a critical section implementation for single-threaded environment
// struct SingleThreadedCriticalSection;
// critical_section::set_impl!(SingleThreadedCriticalSection);

// unsafe impl critical_section::Impl for SingleThreadedCriticalSection {
//     unsafe fn acquire() -> u8 {
//         // In single-threaded environment, no need to disable interrupts
//         0
//     }

//     unsafe fn release(_token: u8) {
//         // Nothing to restore
//     }
// }

/// Handle GetPublicKey request
fn handle_get_public_key(request_data: &[u8]) -> Result<()> {
    // Deserialize the request
    let request = FunnycoinGetPublicKey::decode(request_data).map_err(|_| Error::InvalidMessage)?;

    info!(
        "GetPublicKey request for path: {:?}",
        request.address_n.as_slice()
    );

    let mut confirm_msg = String::new();
    let mut wa = WriteAdapter(&mut confirm_msg);
    _ = ufmt::uwrite!(
        wa,
        "Confirm Public Key for path: {:?}",
        request.address_n.as_slice()
    );
    match ui::confirm_value("Confirm Public Key", &confirm_msg) {
        Ok(ui::TrezorUiResult::Confirmed) => (),
        Ok(_) => return Err(Error::Cancelled),
        Err(e) => return Err(e.into()),
    }

    // In a real implementation, you would:
    // 1. Derive the key from the BIP-32 path
    // 2. Generate the xpub
    // 3. Show on display if requested

    // For now, create a dummy response
    let mut response = FunnycoinPublicKey::default();
    let mut slice = [0u8; 128];
    let mut writer = trezor_app_sdk::util::SliceWriter::new(&mut slice);
    _ = ufmt::uwrite!(
        writer,
        "xpub_dummy_for_path_{:?}",
        request.address_n.as_slice()
    );
    response.xpub = String::from(writer.as_ref());
    response.public_key = Some(vec![0x04; 65]); // Dummy uncompressed public key

    let response_bytes = response.encode_to_vec();
    let message = IpcMessage::new(FunnycoinMessages::PublicKey.into(), &response_bytes);
    Ok(message.send(service::CORE_SERVICE_REMOTE, CoreIpcService::WireEnd.into())?)
}

// Application entry point - receives raw bytes, returns raw bytes
#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    let message = CORE_SERVICE.receive(Timeout::max())?;
    match message.service().into() {
        CoreIpcService::WireStart => handle_wire_message(&message),
        _ => {
            error!("Invalid service invoked: {:?}, message id {:?}, data {:?}", message.service(), message.id(), message.data());
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
        FunnycoinMessages::GetPublicKey => handle_get_public_key(message.data()),
        _ => Err(Error::InvalidFunction),
    }
}
