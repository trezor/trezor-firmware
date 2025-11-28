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

use rkyv::api::low::deserialize;

// Re-export the archived types for convenience
pub use rkyv::Archived;
use rkyv::rancor::Failure;
use rkyv::to_bytes;
use trezor_structs::{PropsList, ShortString, TrezorUiEnum};
pub use trezor_structs::TrezorUiResult;

use crate::ipc::IpcMessage;
use crate::service::{CoreIpcService, Error, IpcRemote};
use crate::util::Timeout;
pub type ArchivedTrezorUiResult = Archived<TrezorUiResult>;
pub type ArchivedTrezorUiEnum = Archived<TrezorUiEnum>;

// ============================================================================
// Helper Functions
// ============================================================================

static SERVICES: spin::Once<&'static IpcRemote<'static, CoreIpcService>> = spin::Once::new();

type Result<T> = core::result::Result<T, Error<'static>>;
type UiResult = Result<TrezorUiResult>;

pub fn init(services: &'static IpcRemote<CoreIpcService>) {
    SERVICES.call_once(|| services);
}

fn services_or_die() -> &'static IpcRemote<'static, CoreIpcService> {
    SERVICES.get().expect("Services not initialized")
}

/// Send a UI enum over IPC and get the response
fn ipc_ui_call(value: &TrezorUiEnum) -> UiResult {
    let bytes = to_bytes::<Failure>(value).unwrap();
    let message = IpcMessage::new(0, &bytes);
    let result = services_or_die().call(CoreIpcService::Ui, &message, Timeout::max())?;
    let archived = unsafe { rkyv::access_unchecked::<ArchivedTrezorUiResult>(result.data()) };
    let deserialized = deserialize::<TrezorUiResult, Failure>(archived).unwrap();
    Ok(deserialized)
}

/// Send a UI call and expect a boolean confirmation result
fn ipc_ui_call_confirm(value: TrezorUiEnum) -> UiResult {
    match ipc_ui_call(&value)? {
        TrezorUiResult::Confirmed => Ok(TrezorUiResult::Confirmed),
        _ => Ok(TrezorUiResult::Cancelled),
    }
}

/// Send a UI call that doesn't expect a meaningful response
fn ipc_ui_call_void(value: TrezorUiEnum) -> Result<()> {
    ipc_ui_call(&value)?;
    Ok(())
}

// ============================================================================
// Public API Functions
// ============================================================================

/// Show a confirmation dialog with title and content
///
/// Returns `Ok(true)` if user confirms, `Ok(false)` if user cancels
pub fn confirm_value(title: &str, content: &str) -> UiResult {
    let value = TrezorUiEnum::ConfirmAction {
        title: ShortString::from_str(title).unwrap(),
        content: ShortString::from_str(&content[..50]).unwrap(),
    };
    ipc_ui_call_confirm(value)
}

/// Show a confirmation dialog with a list of key-value properties
///
/// Returns `Ok(true)` if user confirms, `Ok(false)` if user cancels
pub fn confirm_properties(title: &str, props: &[(&str, &str)]) -> UiResult {
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
pub fn request_string(prompt: &str) -> UiResult {
    let value = TrezorUiEnum::RequestString {
        prompt: ShortString::from_str(prompt).unwrap(),
    };
    let result = ipc_ui_call(&value)?;
    match result {
        TrezorUiResult::String(_) => Ok(result),
        _ => Ok(TrezorUiResult::Cancelled),
    }
}

/// Request a number from the user within a range
pub fn request_number(title: &str, content: &str, initial: u32, min: u32, max: u32) -> UiResult {
    let value = TrezorUiEnum::RequestNumber {
        title: ShortString::from_str(title).unwrap(),
        content: ShortString::from_str(content).unwrap(),
        initial,
        min,
        max,
    };

    let result = ipc_ui_call(&value)?;
    match result {
        TrezorUiResult::Integer(_) => Ok(result),
        _ => Ok(TrezorUiResult::Cancelled),
    }
}

/// Send a ping message (for testing)
pub fn ping(msg: &str) -> Result<()> {
    let ping = IpcMessage::new(0, msg.as_bytes());
    let resp = services_or_die().call(CoreIpcService::Ping, &ping, Timeout::max())?;
    if resp.data() == msg.as_bytes() {
        Ok(())
    } else {
        Err(Error::UnexpectedResponse(resp))
    }
}
