#![no_std]
#![no_main]

extern crate alloc;

use alloc::format;
use alloc::string::String;
use alloc::vec;
use alloc::vec::Vec;
use prost::Message;
use trezor_app_sdk::ui::{
    confirm_properties, confirm_value, request_number, request_string, show_success, show_warning,
};
pub use trezor_app_sdk::{debug, error, info, trace, warn, Result};

// Include generated protobuf code
mod funnycoin_proto {
    include!(concat!(env!("OUT_DIR"), "/funnycoin.rs"));
}
use funnycoin_proto::{FunnycoinGetPublicKey, FunnycoinPublicKey};

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
fn handle_get_public_key(request_data: &[u8]) -> Result<Vec<u8>> {
    use trezor_app_sdk::ApiError;

    // Deserialize the request
    let request =
        FunnycoinGetPublicKey::decode(request_data).map_err(|_| ApiError::InvalidMessage)?;

    info!("GetPublicKey request for path: {:?}", request.address_n);

    // In a real implementation, you would:
    // 1. Derive the key from the BIP-32 path
    // 2. Generate the xpub
    // 3. Show on display if requested

    // For now, create a dummy response
    let mut response = FunnycoinPublicKey::default();
    response.xpub = format!("xpub_dummy_for_path_{:?}", request.address_n);
    response.public_key = Some(vec![0x04; 65]); // Dummy uncompressed public key

    // Serialize the response
    Ok(response.encode_to_vec())
}

// Application entry point - receives raw bytes, returns raw bytes
#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    let str1 = String::from("title");

    let number = request_number("Number Input", "Insert any number", 0, 0, 100)?;
    let str = request_string("String Input")?;
    let confirm = format!("Confirm Number: {}, String: {}?", number, str.as_str());
    let strnum = format!("{}", number);
    let props = [
        ("Number Input", strnum.as_str()),
        ("String Input", str.as_str()),
    ];
    confirm_value(&str1, &confirm)?;
    warn!("User is about to confirm properties");
    match confirm_properties("title", &props[..])? {
        true => show_success("success", "operation confirmed")?,
        false => show_warning("warning", "operation cancelled")?,
    };

    Ok(())
}

/// Entry point for handling protobuf function calls
/// fn_id: function identifier
/// data: serialized protobuf request
/// Returns: serialized protobuf response
#[unsafe(no_mangle)]
pub extern "C" fn handle_call(fn_id: u32, data: *const u8, data_len: usize) -> *mut u8 {
    use trezor_app_sdk::low_level_api::ApiError;

    // Convert raw pointer to slice
    let request_data = unsafe { core::slice::from_raw_parts(data, data_len) };

    let response = match fn_id {
        0 => handle_get_public_key(request_data),
        _ => Err(ApiError::InvalidFunction),
    };

    // For now, just return null - proper IPC handling will come later
    core::ptr::null_mut()
}
