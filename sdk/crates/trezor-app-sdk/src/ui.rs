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

// Re-export the archived types for convenience
pub use rkyv::Archived;
use rkyv::api::low::deserialize;
use rkyv::rancor::Failure;
use rkyv::to_bytes;
pub use trezor_structs::TrezorUiResult;
use trezor_structs::{
    ArchivedUtilEnum, LongString, PropsList, ShortString, StrExtList, TrezorUiEnum,
};

use crate::core_services::services_or_die;
use crate::error;
use crate::ipc::IpcMessage;
use crate::service::{
    CoreIpcService, Error, NoUtilHandler, UtilContext, UtilHandleResult, UtilHandler,
};
use crate::util::Timeout;

pub type ArchivedTrezorUiResult = Archived<TrezorUiResult>;
pub type ArchivedTrezorUiEnum = Archived<TrezorUiEnum>;

pub const CHARS_PER_PAGE: usize = 96;

/// Long content handler - responds to page requests
pub struct LongContentHandler<'a>(pub &'a str);

impl<'a> LongContentHandler<'a> {
    fn send_page(&self, ctx: &UtilContext, page_idx: usize) {
        let long_content = self.0;

        // Find byte range for the requested char slice
        let mut chars = long_content.chars();
        let start_byte = chars
            .by_ref()
            .take(page_idx * crate::ui::CHARS_PER_PAGE)
            .map(|c| c.len_utf8())
            .sum::<usize>();
        let slice_len = chars
            .take(crate::ui::CHARS_PER_PAGE)
            .map(|c| c.len_utf8())
            .sum::<usize>();
        let slice = &long_content.as_bytes()[start_byte..start_byte + slice_len];

        // Send response with the same service ID as the request
        let _ = IpcMessage::new(ctx.id, slice).send(ctx.remote, ctx.service);
    }
}

impl<'a> UtilHandler for LongContentHandler<'a> {
    fn expects_util_messages(&self) -> bool {
        true
    }

    fn handle(&self, ctx: &UtilContext, archived: &ArchivedUtilEnum) -> UtilHandleResult {
        match archived {
            ArchivedUtilEnum::RequestPage { idx } => {
                let page_idx = idx.to_native() as usize;
                self.send_page(ctx, page_idx);
                UtilHandleResult::Continue
            }
        }
    }
}

// ============================================================================
// Helper Functions
// ============================================================================

type Result<T> = core::result::Result<T, Error<'static>>;
type UiResult = Result<TrezorUiResult>;

fn ipc_ui_call(value: &TrezorUiEnum) -> UiResult {
    ipc_ui_call_ext(value, &NoUtilHandler {})
}

fn ipc_ui_call_ext(value: &TrezorUiEnum, util_handler: &dyn UtilHandler) -> UiResult {
    let bytes = to_bytes::<Failure>(value).unwrap();
    let message = IpcMessage::new(0, &bytes);

    let result =
        services_or_die().call(CoreIpcService::Ui, &message, Timeout::max(), util_handler)?;
    // Safe validation using bytecheck before accessing archived data
    let archived = rkyv::access::<ArchivedTrezorUiResult, Failure>(result.data()).unwrap();
    let deserialized = deserialize::<TrezorUiResult, Failure>(archived).unwrap();
    Ok(deserialized)
}

/// Send a UI call and expect a boolean confirmation result
fn ipc_ui_call_confirm(value: &TrezorUiEnum) -> UiResult {
    match ipc_ui_call(value) {
        Ok(TrezorUiResult::Confirmed) => Ok(TrezorUiResult::Confirmed),
        Ok(_) => Ok(TrezorUiResult::Cancelled),
        Err(e) => {
            error!("UI error: {:?}", e);
            Err(e)
        }
    }
}

/// Send a UI call that doesn't expect a meaningful response
fn ipc_ui_call_void(value: &TrezorUiEnum) -> Result<()> {
    ipc_ui_call(value)?;
    Ok(())
}

// ============================================================================
// Public API Functions
// ============================================================================

/// Show a confirmation dialog with title and content
///
/// Returns `Ok(true)` if user confirms, `Ok(false)` if user cancels
pub fn confirm_value(title: &str, content: &str) -> UiResult {
    debug_assert!(title.len() <= 50, "title too long");
    debug_assert!(content.len() <= 50, "content too long");

    let value = TrezorUiEnum::ConfirmValue {
        title: ShortString::from_str(title).unwrap(),
        content: ShortString::from_str(content).unwrap(),
    };
    ipc_ui_call_confirm(&value)
}

pub fn confirm_action(title: &str, action: &str, hold: bool) -> UiResult {
    debug_assert!(title.len() <= 50, "title too long");
    debug_assert!(action.len() <= 50, "action too long");

    let value = TrezorUiEnum::ConfirmAction {
        title: ShortString::from_str(title).unwrap(),
        action: ShortString::from_str(action).unwrap(),
        hold,
    };
    ipc_ui_call_confirm(&value)
}

pub fn confirm_long_value(title: &str, content: &str) -> UiResult {
    let value = TrezorUiEnum::ConfirmLong {
        title: ShortString::from_str(title).unwrap(),
        pages: (content.chars().count() as usize + CHARS_PER_PAGE - 1) / CHARS_PER_PAGE,
    };

    match ipc_ui_call_ext(&value, &LongContentHandler(content)) {
        Ok(TrezorUiResult::Confirmed) => Ok(TrezorUiResult::Confirmed),
        Ok(_) => Ok(TrezorUiResult::Cancelled),
        Err(e) => {
            error!("UI error: {:?}", e);
            Err(e)
        }
    }
}

/// Show a confirmation dialog with a list of key-value properties
///
/// Returns `Ok(true)` if user confirms, `Ok(false)` if user cancels
pub fn confirm_properties(title: &str, props: &[(&str, &str)]) -> UiResult {
    let value = TrezorUiEnum::ConfirmProperties {
        title: ShortString::from_str(title).unwrap(),
        props: PropsList::from_prop_slice(props).unwrap(),
    };
    ipc_ui_call_confirm(&value)
}

/// Show a warning message
pub fn show_warning(title: &str, content: &str) -> Result<()> {
    let value = TrezorUiEnum::Warning {
        title: ShortString::from_str(title).unwrap(),
        content: ShortString::from_str(content).unwrap(),
    };
    ipc_ui_call_void(&value)
}

/// Show a danger message
pub fn show_danger(title: &str, content: &str) -> UiResult {
    let value = TrezorUiEnum::Danger {
        title: ShortString::from_str(title).unwrap(),
        content: ShortString::from_str(content).unwrap(),
    };
    ipc_ui_call_confirm(&value)
}

/// Show a success message
pub fn show_success(title: &str, content: &str) -> Result<()> {
    let value = TrezorUiEnum::Success {
        title: ShortString::from_str(title).unwrap(),
        content: ShortString::from_str(content).unwrap(),
    };
    ipc_ui_call_void(&value)
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

pub fn show_public_key(key: &str) -> UiResult {
    let value = TrezorUiEnum::ShowPublicKey {
        key: LongString::from_str(key).unwrap(),
    };
    ipc_ui_call_confirm(&value)
}

pub fn should_show_more(title: &str, para: &[(&str, bool)], button_text: &str) -> UiResult {
    let value = TrezorUiEnum::ShouldShowMore {
        title: ShortString::from_str(title).unwrap(),
        items: StrExtList::from_str_slice(para).unwrap(),
        button_text: ShortString::from_str(button_text).unwrap(),
    };
    ipc_ui_call_confirm(&value)
}
