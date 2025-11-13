//! High-level UI API
//!
//! This module provides user-friendly functions for interacting with the Trezor UI.
//!
//! ## Examples
//!
//! ```rust
//! use trezor_app_sdk::ui;
//!
//! // Show confirmation dialog
//! if ui::confirm_value("Title", "Confirm this?")? {
//!     ui::show_success("Success", "Confirmed!")?;
//! }
//!
//! // Request user input
//! let name = ui::request_string("Enter name:")?;
//! let amount = ui::request_number("Amount", "Enter amount", 0, 0, 100)?;
//! ```

extern crate alloc;

use alloc::string::String;
use core::str::FromStr;
use rkyv::{rancor::Failure, to_bytes};

use crate::low_level_api::{sysevents_t, Api, ApiError, ApiWrapper, IpcMessage};
use crate::{trace, Result};
use trezor_structs::{PropsList, ShortString, TrezorUiEnum, TrezorUiResult};

// Re-export the archived types for convenience
pub use rkyv::Archived;
pub type ArchivedTrezorUiResult = Archived<TrezorUiResult>;
pub type ArchivedTrezorUiEnum = Archived<TrezorUiEnum>;

// ============================================================================
// Helper Functions
// ============================================================================

/// Send a UI enum over IPC and get the response
fn ipc_ui_call(value: &TrezorUiEnum, timeout: u32) -> Result<IpcMessage> {
    let bytes = to_bytes::<Failure>(value).unwrap();
    let mut response = IpcMessage::default();
    trace!("sending {} bytes", bytes.len());

    match Api::ipc_call(1, 0, &bytes, &mut response, timeout)? {
        true => Ok(response),
        false => Err(ApiError::Failed),
    }
}

/// Get the archived result from an IPC response
fn get_archived_result(response: &IpcMessage) -> &ArchivedTrezorUiResult {
    let slice = unsafe {
        core::slice::from_raw_parts(
            response.inner().data as *const u8,
            response.inner().size as usize,
        )
    };
    unsafe { rkyv::access_unchecked::<ArchivedTrezorUiResult>(slice) }
}

/// Send a UI call and expect a boolean confirmation result
fn ipc_ui_call_confirm(value: TrezorUiEnum) -> Result<bool> {
    let response = ipc_ui_call(&value, i32::MAX as _)?;
    let archived = get_archived_result(&response);

    match archived {
        ArchivedTrezorUiResult::Confirmed => Ok(true),
        ArchivedTrezorUiResult::Cancelled => Ok(false),
        _ => Err(ApiError::Failed),
    }
}

/// Send a UI call that doesn't expect a meaningful response
fn ipc_ui_call_void(value: TrezorUiEnum) -> Result<()> {
    ipc_ui_call(&value, i32::MAX as _)?;
    Ok(())
}

// ============================================================================
// Public API Functions
// ============================================================================

/// Show a confirmation dialog with title and content
///
/// Returns `Ok(true)` if user confirms, `Ok(false)` if user cancels
pub fn confirm_value(title: &str, content: &str) -> Result<bool> {
    let value = TrezorUiEnum::ConfirmAction {
        title: ShortString::from_str(title).unwrap(),
        content: ShortString::from_str(content).unwrap(),
    };
    ipc_ui_call_confirm(value)
}

/// Show a confirmation dialog with a list of key-value properties
///
/// Returns `Ok(true)` if user confirms, `Ok(false)` if user cancels
pub fn confirm_properties(title: &str, props: &[(&str, &str)]) -> Result<bool> {
    let value = TrezorUiEnum::ConfirmProperties {
        title: ShortString::from_str(title).unwrap(),
        props: PropsList::from_prop_slice(props).unwrap(),
    };
    ipc_ui_call_confirm(value)
}

/// Show a warning message
pub fn show_warning(title: &str, content: &str) -> Result<()> {
    let value = TrezorUiEnum::Warning {
        title: ShortString::from_str(title).unwrap(),
        content: ShortString::from_str(content).unwrap(),
    };
    ipc_ui_call_void(value)
}

/// Show a success message
pub fn show_success(title: &str, content: &str) -> Result<()> {
    let value = TrezorUiEnum::Success {
        title: ShortString::from_str(title).unwrap(),
        content: ShortString::from_str(content).unwrap(),
    };
    ipc_ui_call_void(value)
}

/// Request string input from the user
pub fn request_string(prompt: &str) -> Result<String> {
    let value = TrezorUiEnum::RequestString {
        prompt: ShortString::from_str(prompt).unwrap(),
    };

    let response = ipc_ui_call(&value, i32::MAX as _)?;
    let archived = get_archived_result(&response);

    match archived {
        ArchivedTrezorUiResult::String(s) => {
            let len = s.len as usize;
            let slice = &s.data[..len];
            let string = String::from_str(core::str::from_utf8(slice).unwrap()).unwrap();
            Ok(string)
        }
        _ => Err(ApiError::Failed),
    }
}

/// Request a number from the user within a range
pub fn request_number(title: &str, content: &str, initial: u32, min: u32, max: u32) -> Result<u32> {
    let value = TrezorUiEnum::RequestNumber {
        title: ShortString::from_str(title).unwrap(),
        content: ShortString::from_str(content).unwrap(),
        initial,
        min,
        max,
    };

    let response = ipc_ui_call(&value, i32::MAX as _)?;
    let archived = get_archived_result(&response);

    match archived {
        ArchivedTrezorUiResult::Integer(n) => Ok((*n).into()),
        _ => Err(ApiError::Failed),
    }
}

/// Sleep for specified milliseconds
pub fn sleep(ms: u32) -> Result<()> {
    let deadline = Api::systick_ms()?.wrapping_add(ms);
    let awaited = sysevents_t::default();
    let mut signalled = sysevents_t::default();
    Api::sysevents_poll(&awaited, &mut signalled, deadline)
}

/// Send a ping message (for testing)
pub fn ping(msg: &str) -> Result<()> {
    let mut resp = IpcMessage::default();
    match Api::ipc_call(1, 1, msg.as_bytes(), &mut resp, 1000)? {
        true => Ok(()),
        false => Err(ApiError::Failed),
    }
}

/// Request to finish and exit the application
pub fn request_finish() -> Result<bool> {
    Api::ipc_send(1, 2, &[])
}
