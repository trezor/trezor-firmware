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
    ArchivedUtilEnum, ExtraLongString, LongString, PropsList, ShortString, StrExtList, TrezorUiEnum,
};

use crate::core_services::services_or_die;
use crate::ipc::IpcMessage;
use crate::service::{
    CoreIpcService, Error, NoUtilHandler, UtilContext, UtilHandleResult, UtilHandler,
};
use crate::util::Timeout;
use crate::{error, unwrap};

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
pub type UiResult = Result<TrezorUiResult>;

fn ipc_ui_call(value: &TrezorUiEnum) -> UiResult {
    ipc_ui_call_ext(value, &NoUtilHandler {})
}

fn ipc_ui_call_ext(value: &TrezorUiEnum, util_handler: &dyn UtilHandler) -> UiResult {
    let bytes = to_bytes::<Failure>(value).map_err(|_| Error::FailedToSend)?;
    let message = IpcMessage::new(0, &bytes);

    let result =
        services_or_die().call(CoreIpcService::Ui, &message, Timeout::max(), util_handler)?;
    // Safe validation using bytecheck before accessing archived data
    let archived = unwrap!(rkyv::access::<ArchivedTrezorUiResult, Failure>(
        result.data()
    ));
    let deserialized = unwrap!(deserialize::<TrezorUiResult, Failure>(archived));
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

pub fn confirm_linear_flow(confirm_factories: &[&dyn Fn() -> UiResult]) -> UiResult {
    let mut i = 0usize;

    while i < confirm_factories.len() {
        let res = (confirm_factories[i])()?;

        match res {
            TrezorUiResult::Confirmed => {
                i += 1;
            }
            TrezorUiResult::Back if i > 0 => {
                i -= 1;
            }
            _ => {
                return Ok(TrezorUiResult::Cancelled);
            }
        }
    }

    Ok(TrezorUiResult::Confirmed)
}

// ============================================================================
// Public API Functions
// ============================================================================

/// Show a confirmation dialog with title and content
///
/// Returns `Ok(true)` if user confirms, `Ok(false)` if user cancels
pub fn confirm_value_simple(
    title: &str,
    content: &str,
    description: Option<&str>,
    br_name: &str,
    br_code: Option<u32>,
    is_data: bool,
    verb: Option<&str>,
    subtitle: Option<&str>,
    hold: bool,
    chunkify: bool,
    page_counter: bool,
    cancel: bool,
) -> UiResult {
    match confirm_value_inner(
        title,
        content,
        description,
        br_name,
        br_code,
        is_data,
        verb,
        subtitle,
        false,
        hold,
        chunkify,
        page_counter,
        cancel,
    ) {
        Ok(TrezorUiResult::Confirmed) => Ok(TrezorUiResult::Confirmed),
        Ok(_) => Ok(TrezorUiResult::Cancelled),
        Err(e) => {
            error!("UI error: {:?}", e);
            Err(e)
        }
    }
}

fn confirm_value_inner(
    title: &str,
    content: &str,
    description: Option<&str>,
    br_name: &str,
    br_code: Option<u32>,
    is_data: bool,
    verb: Option<&str>,
    subtitle: Option<&str>,
    info: bool,
    hold: bool,
    chunkify: bool,
    page_counter: bool,
    cancel: bool,
) -> UiResult {
    let br_code = br_code.unwrap_or(1); /* ButtonRequest_Other = 1 */

    let value = TrezorUiEnum::ConfirmValue {
        title: ShortString::from_str(title).map_err(|_| Error::FailedToSend)?,
        value: ExtraLongString::from_str(content).map_err(|_| Error::FailedToSend)?,
        description: description
            .map(|d| ShortString::from_str(d).map_err(|_| Error::FailedToSend))
            .transpose()?,
        is_data,
        subtitle: subtitle
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
        verb: verb
            .map(|v| ShortString::from_str(v).map_err(|_| Error::FailedToSend))
            .transpose()?,
        info,
        hold,
        chunkify,
        page_counter,
        cancel,
        br_name: ShortString::from_str(br_name).map_err(|_| Error::FailedToSend)?,
        br_code,
    };
    ipc_ui_call(&value)
}

pub fn confirm_blob(
    title: &str,
    data: &str,
    description: Option<&str>,
    subtitle: Option<&str>,
    br_name: &str,
    br_code: u32,
    hold: bool,
    verb: Option<&str>,
    verb_cancel: Option<&str>,
    chunkify: bool,
    ask_pagination: bool,
) -> UiResult {
    let value = TrezorUiEnum::ConfirmBlob {
        title: ShortString::from_str(title).map_err(|_| Error::FailedToSend)?,
        data: ExtraLongString::from_str(data).map_err(|_| Error::FailedToSend)?,
        description: description
            .map(|d| ShortString::from_str(d).map_err(|_| Error::FailedToSend))
            .transpose()?,
        subtitle: subtitle
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
        hold,
        chunkify,
        verb: verb
            .map(|v| ShortString::from_str(v).map_err(|_| Error::FailedToSend))
            .transpose()?,
        verb_cancel: verb_cancel
            .map(|v| ShortString::from_str(v).map_err(|_| Error::FailedToSend))
            .transpose()?,
        is_data: true,
        br_code: br_code,
        br_name: ShortString::from_str(br_name).map_err(|_| Error::FailedToSend)?,
        ask_pagination,
    };
    ipc_ui_call_confirm(&value)
}

fn show_info(title: &str, items: &[(&str, &str, bool)], chunkify: bool) -> UiResult {
    let value = TrezorUiEnum::ShowInfo {
        title: ShortString::from_str(title).map_err(|_| Error::FailedToSend)?,
        items: PropsList::from_prop_slice(items).map_err(|_| Error::FailedToSend)?,
        chunkify,
    };
    ipc_ui_call_confirm(&value)
}

pub fn confirm_value_with_info(
    title: &str,
    content: &str,
    description: Option<&str>,
    br_name: &str,
    br_code: Option<u32>,
    is_data: bool,
    verb: Option<&str>,
    subtitle: Option<&str>,
    hold: bool,
    chunkify: bool,
    page_counter: bool,
    cancel: bool,
    info_title: &str,
    info_items: &[(&str, &str, bool)],
    info_chunkify: bool,
) -> UiResult {
    match confirm_value_inner(
        title,
        content,
        description,
        br_name,
        br_code,
        is_data,
        verb,
        subtitle,
        true,
        hold,
        chunkify,
        page_counter,
        cancel,
    ) {
        Ok(TrezorUiResult::Confirmed) => Ok(TrezorUiResult::Confirmed),
        Ok(TrezorUiResult::Info) => show_info(info_title, info_items, info_chunkify),
        Ok(_) => Ok(TrezorUiResult::Cancelled),
        Err(e) => {
            error!("UI error: {:?}", e);
            Err(e)
        }
    }
}

pub fn confirm_summary(
    title: Option<&str>,
    amount: Option<&str>,
    amount_label: Option<&str>,
    fee: &str,
    fee_label: &str,
    account_title: Option<&str>,
    account_items: Option<&[(&str, &str, bool)]>,
    extra_title: Option<&str>,
    extra_items: Option<&[(&str, &str, bool)]>,
    back_button: bool,
    br_name: Option<&str>,
    br_code: Option<u32>,
) -> UiResult {
    let br_name = br_name.unwrap_or("confirm_total");
    let br_code = br_code.unwrap_or(8); /* ButtonRequest_SignTx */
    let value = TrezorUiEnum::ConfirmSummary {
        title: ShortString::from_str(title.unwrap_or("Send")).map_err(|_| Error::FailedToSend)?,
        amount: amount
            .map(|a| ShortString::from_str(a).map_err(|_| Error::FailedToSend))
            .transpose()?,
        amount_label: amount_label
            .map(|l| ShortString::from_str(l).map_err(|_| Error::FailedToSend))
            .transpose()?,
        fee: ShortString::from_str(fee).map_err(|_| Error::FailedToSend)?,
        fee_label: ShortString::from_str(fee_label).map_err(|_| Error::FailedToSend)?,
        account_title: account_title
            .map(|t| ShortString::from_str(t).map_err(|_| Error::FailedToSend))
            .transpose()?,
        account_items: account_items
            .map(|items| PropsList::from_prop_slice(items).map_err(|_| Error::FailedToSend))
            .transpose()?,
        extra_title: extra_title
            .map(|t| ShortString::from_str(t).map_err(|_| Error::FailedToSend))
            .transpose()?,
        extra_items: extra_items
            .map(|items| PropsList::from_prop_slice(items).map_err(|_| Error::FailedToSend))
            .transpose()?,
        back_button: back_button,
        br_name: ShortString::from_str(br_name).map_err(|_| Error::FailedToSend)?,
        br_code: br_code,
    };
    ipc_ui_call_confirm(&value)
}

pub fn confirm_action(title: &str, action: &str, hold: bool) -> UiResult {
    let value = TrezorUiEnum::ConfirmAction {
        title: ShortString::from_str(title).map_err(|_| Error::FailedToSend)?,
        action: ShortString::from_str(action).map_err(|_| Error::FailedToSend)?,
        hold,
    };
    ipc_ui_call_confirm(&value)
}

pub fn confirm_long_value(title: &str, content: &str) -> UiResult {
    let value = TrezorUiEnum::ConfirmLong {
        title: ShortString::from_str(title).map_err(|_| Error::FailedToSend)?,
        pages: (content.chars().count() + CHARS_PER_PAGE - 1) / CHARS_PER_PAGE,
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
pub fn confirm_properties(
    title: &str,
    props: &[(&str, &str, bool)],
    subtitle: Option<&str>,
    verb: Option<&str>,
    hold: bool,
    br_name: &str,
    br_code: Option<u32>,
) -> UiResult {
    let value = TrezorUiEnum::ConfirmProperties {
        title: ShortString::from_str(title).map_err(|_| Error::FailedToSend)?,
        props: PropsList::from_prop_slice(props).map_err(|_| Error::FailedToSend)?,
        subtitle: subtitle
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
        verb: verb
            .map(|v| ShortString::from_str(v).map_err(|_| Error::FailedToSend))
            .transpose()?,
        hold,
        br_name: ShortString::from_str(br_name).map_err(|_| Error::FailedToSend)?,
        br_code: br_code.unwrap_or(3), /* ButtonRequest_ConfirmOutput */
    };
    ipc_ui_call_confirm(&value)
}

/// Show a warning message
pub fn show_warning(title: &str, content: &str, br_name: &str, br_code: Option<u32>) -> Result<()> {
    let value = TrezorUiEnum::Warning {
        title: ShortString::from_str(title).map_err(|_| Error::FailedToSend)?,
        content: ShortString::from_str(content).map_err(|_| Error::FailedToSend)?,
        br_name: ShortString::from_str(br_name).map_err(|_| Error::FailedToSend)?,
        br_code: br_code.unwrap_or(18), /* ButtonRequestType.Warning */
    };
    ipc_ui_call_void(&value)
}

/// Show a mismatch message
pub fn show_mismatch(title: &str) -> UiResult {
    let value = TrezorUiEnum::Mismatch {
        title: ShortString::from_str(title).map_err(|_| Error::FailedToSend)?,
    };
    ipc_ui_call_confirm(&value)
}

/// Show a danger message
pub fn show_danger(title: &str, content: &str, br_name: &str, br_code: Option<u32>) -> UiResult {
    let value = TrezorUiEnum::Danger {
        title: ShortString::from_str(title).map_err(|_| Error::FailedToSend)?,
        content: ShortString::from_str(content).map_err(|_| Error::FailedToSend)?,
        br_name: ShortString::from_str(br_name).map_err(|_| Error::FailedToSend)?,
        br_code: br_code.unwrap_or(18), /* ButtonRequestType.Warning */
    };
    ipc_ui_call_confirm(&value)
}

/// Show a success message
pub fn show_success(content: &str, br_name: &str) -> Result<()> {
    let value = TrezorUiEnum::Success {
        content: ShortString::from_str(content).map_err(|_| Error::FailedToSend)?,
        br_name: ShortString::from_str(br_name).map_err(|_| Error::FailedToSend)?,
    };
    ipc_ui_call_void(&value)
}

/// Request a number from the user within a range
pub fn request_number(title: &str, content: &str, initial: u32, min: u32, max: u32) -> UiResult {
    let value = TrezorUiEnum::RequestNumber {
        title: ShortString::from_str(title).map_err(|_| Error::FailedToSend)?,
        content: ShortString::from_str(content).map_err(|_| Error::FailedToSend)?,
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

pub fn show_public_key(
    key: &str,
    title: Option<&str>,
    account: Option<&str>,
    path: Option<&str>,
    warning: Option<&str>,
    br_name: Option<&str>,
) -> UiResult {
    let value = TrezorUiEnum::ShowPublicKey {
        pubkey: LongString::from_str(key).map_err(|_| Error::FailedToSend)?,
        title: title
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
        account: account
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
        path: path
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
        warning: warning
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
        br_name: br_name
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
    };
    ipc_ui_call_confirm(&value)
}

pub fn should_show_more(
    title: &str,
    para: &[(&str, bool)],
    button_text: &str,
    br_name: Option<&str>,
) -> Result<bool> {
    let br_name = br_name.unwrap_or("should_show_more");
    let value = TrezorUiEnum::ShouldShowMore {
        title: ShortString::from_str(title).map_err(|_| Error::FailedToSend)?,
        items: StrExtList::from_str_slice(para).map_err(|_| Error::FailedToSend)?,
        button_text: ShortString::from_str(button_text).map_err(|_| Error::FailedToSend)?,
        br_name: ShortString::from_str(br_name).map_err(|_| Error::FailedToSend)?,
    };
    // TODO: move mapping to the coreapp
    match ipc_ui_call(&value) {
        Ok(TrezorUiResult::Confirmed) => Ok(false),
        Ok(TrezorUiResult::Info) => Ok(true),
        _ => {
            // TODO: error handling
            Err(Error::Timeout)
        }
    }
}

pub fn show_address(
    address: &str,
    title: Option<&str>,
    subtitle: Option<&str>,
    account: Option<&str>,
    path: Option<&str>,
    xpubs: &[(&str, &str, bool)],
    chunkify: Option<bool>,
) -> UiResult {
    let value = TrezorUiEnum::ShowAddress {
        address: ShortString::from_str(address).map_err(|_| Error::FailedToSend)?,
        title: title
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
        subtitle: subtitle
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
        account: account
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
        path: path
            .map(|s| ShortString::from_str(s).map_err(|_| Error::FailedToSend))
            .transpose()?,
        xpubs: PropsList::from_prop_slice(xpubs).map_err(|_| Error::FailedToSend)?,
        chunkify,
    };
    ipc_ui_call_confirm(&value)
}
