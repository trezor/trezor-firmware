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
use trezor_structs::{ArchivedUtilEnum, PropsList, StrExtList, StrList, TrezorUiEnum};
pub use trezor_structs::{TrezorProgressEnum, TrezorUiResult};

use crate::core_services::services_or_die;
use crate::ipc::IpcMessage;
use crate::service::{
    CoreIpcService, Error, NoUtilHandler, UtilContext, UtilHandleResult, UtilHandler,
};
use crate::util::Timeout;
use crate::{error, info, unwrap};

pub type ArchivedTrezorUiResult = Archived<TrezorUiResult>;
pub type ArchivedTrezorUiEnum<'a> = Archived<TrezorUiEnum<'a>>;

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
    info!("serializing message");
    let bytes = to_bytes::<Failure>(value).map_err(|_| Error::FailedToSend)?;
    let message = IpcMessage::new(0, &bytes);
    info!("sending message with size {} bytes", bytes.len());
    let result =
        services_or_die().call(CoreIpcService::Ui, &message, Timeout::max(), util_handler)?;
    // Safe validation using bytecheck before accessing archived data
    info!("validating message");
    let archived = unwrap!(rkyv::access::<ArchivedTrezorUiResult, Failure>(
        result.data()
    ));
    info!("deserializing message");
    let deserialized = unwrap!(deserialize::<TrezorUiResult, Failure>(archived));
    info!("UI call deserialized successfully");
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

fn ipc_progress_call(value: &TrezorProgressEnum) -> Result<()> {
    let bytes = to_bytes::<Failure>(value).map_err(|_| Error::FailedToSend)?;
    let message = IpcMessage::new(value.id(), &bytes);
    let _ = services_or_die().call(
        CoreIpcService::Progress,
        &message,
        Timeout::max(),
        &NoUtilHandler {},
    )?;
    Ok(())
}

pub fn init_progress(
    description: Option<&str>,
    title: Option<&str>,
    indeterminate: bool,
    danger: bool,
) -> Result<()> {
    let value = TrezorProgressEnum::Init {
        description: description.map(|d| d.into()),
        title: title.map(|t| t.into()),
        indeterminate,
        danger,
    };
    ipc_progress_call(&value)
}

pub fn update_progress(description: Option<&str>, value: u32) -> Result<()> {
    let value = TrezorProgressEnum::Update {
        description: description.map(|d| d.into()),
        value,
    };
    ipc_progress_call(&value)
}

pub fn end_progress() -> Result<()> {
    let value = TrezorProgressEnum::End;
    ipc_progress_call(&value)
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
            TrezorUiResult::Cancelled => {
                return Ok(TrezorUiResult::Cancelled);
            }
            _ => {
                // TODO: proper error type
                return Err(Error::Timeout);
            }
        }
    }

    Ok(TrezorUiResult::Confirmed)
}

pub fn error_if_not_confirmed(result: TrezorUiResult) -> core::result::Result<(), crate::Error> {
    if matches!(result, TrezorUiResult::Confirmed) {
        Ok(())
    } else {
        Err(crate::Error::Cancelled)
    }
}

/// Main + info flow:
/// - main progresses like `confirm_linear_flow`
/// - if a main step returns Info, run the info flow
/// - after info flow, always return to the same main step
/// - if `info_layout_can_confirm` and the info flow ends with Confirmed => finish
pub fn interact_with_info_flow(
    main_layout: impl for<'a> Fn(Option<&'a str>) -> UiResult,
    info_layout: impl for<'a> Fn(Option<&'a str>) -> UiResult,
    br_name: &str,
    repeat_button_request: Option<bool>,
    info_layout_can_confirm: Option<bool>,
) -> UiResult {
    let repeat_button_request = repeat_button_request.unwrap_or(false);
    let info_layout_can_confirm = info_layout_can_confirm.unwrap_or(false);

    let mut first_br = Some(br_name);
    let next_br = if repeat_button_request {
        Some(br_name)
    } else {
        None
    };

    loop {
        let main_res = main_layout(first_br)?;

        first_br = next_br;
        match main_res {
            TrezorUiResult::Confirmed => {
                return Ok(TrezorUiResult::Confirmed);
            }
            TrezorUiResult::Info => {
                let info_res = info_layout(next_br)?;

                if info_layout_can_confirm && matches!(info_res, TrezorUiResult::Confirmed) {
                    return Ok(TrezorUiResult::Confirmed);
                } else {
                    // Return to the same main step after info flow.
                    continue;
                }
            }
            TrezorUiResult::Cancelled => {
                return Ok(TrezorUiResult::Cancelled);
            }
            _ => {
                // TODO: proper error type
                return Err(Error::Timeout);
            }
        }
    }
}

pub struct Details<'a> {
    pub name: &'a str,
    pub props: &'a [(&'a str, &'a str, bool)],
    pub title: Option<&'a str>,
    pub subtitle: Option<&'a str>,
    pub br_code: i32,
}

impl<'a> Details<'a> {
    pub fn new(
        name: &'a str,
        props: &'a [(&'a str, &'a str, bool)],
        title: Option<&'a str>,
        subtitle: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            name,
            title,
            props,
            subtitle,
            br_code,
        }
    }

    fn interact(&self) -> Result<()> {
        show_properties(
            self.title.unwrap_or(self.name),
            self.props,
            self.subtitle,
            None,
            self.br_code,
        )
    }
}

pub struct Cancel<'a> {
    pub title: &'a str,
}

impl<'a> Cancel<'a> {
    pub fn new(title: &'a str) -> Self {
        Self { title }
    }

    fn interact(&self) -> UiResult {
        confirm_action(self.title, "", false, None, None, 1)
    }
}

pub struct Menu<'a> {
    children: &'a [Details<'a>],
    cancel: Option<Cancel<'a>>,
}

impl<'a> Menu<'a> {
    const MAX_MENU_ITEMS: usize = 5;

    pub fn new(children: &'a [Details<'a>], cancel: Option<Cancel<'a>>) -> Self {
        Self { children, cancel }
    }

    pub fn interact(&self) -> UiResult {
        if self.children.is_empty() && self.cancel.is_none() {
            // TODO: maybe raise error instead
            return Ok(TrezorUiResult::Confirmed);
        }

        if self.children.len() > Self::MAX_MENU_ITEMS {
            // TODO: proper error type
            return Err(Error::Timeout);
        }

        let mut items = [""; Self::MAX_MENU_ITEMS];
        let mut i = 0usize;
        while i < self.children.len() {
            items[i] = self.children[i].name;
            i += 1;
        }

        loop {
            let choice = select_menu(
                &items[..self.children.len()],
                self.cancel.as_ref().map(|c| c.title),
                1, /* TODO: proper br_code */
            )?;

            match choice {
                TrezorUiResult::Integer(idx) if (idx as usize) < self.children.len() => {
                    // Same behavior as Python: open details, ignore its result, return to menu.
                    let _ = self.children[idx as usize].interact()?;
                    continue;
                }
                TrezorUiResult::Confirmed => {
                    return Ok(TrezorUiResult::Confirmed);
                }
                TrezorUiResult::Cancelled => {
                    if let Some(cancel) = self.cancel.as_ref() {
                        let r = cancel.interact()?;
                        match r {
                            TrezorUiResult::Confirmed => return Ok(TrezorUiResult::Cancelled),
                            TrezorUiResult::Cancelled => continue,
                            // TODO: proper error type
                            _ => return Err(Error::Timeout),
                        }
                    }
                }
                // TODO: proper error type
                _ => return Err(Error::Timeout),
            }
        }
    }
}

pub fn interact_with_menu_flow<'a>(
    main_layout: impl for<'b> Fn(Option<&'b str>) -> UiResult,
    menu: &Menu<'a>,
    br_name: Option<&str>,
) -> UiResult {
    let mut first_br = br_name;

    loop {
        let result = main_layout(first_br)?;
        first_br = None; // ButtonRequest should be sent once (for the main layout)

        if matches!(result, TrezorUiResult::Info) {
            let menu_res = menu.interact()?;
            if matches!(menu_res, TrezorUiResult::Cancelled) {
                return Ok(TrezorUiResult::Cancelled);
            }
            continue;
        }

        return Ok(result);
    }
}

// ============================================================================
// Public API Functions
// ============================================================================

/// Show a confirmation dialog with title and content
///
/// Returns `Ok(true)` if user confirms, `Ok(false)` if user cancels
pub fn confirm_value(
    title: &str,
    content: &str,
    description: Option<&str>,
    br_name: Option<&str>,
    br_code: i32,
    is_data: bool,
    verb: Option<&str>,
    subtitle: Option<&str>,
    info: bool,
    hold: bool,
    chunkify: bool,
    page_counter: bool,
    cancel: bool,
    external_menu: bool,
    warning_footer: Option<&str>,
) -> UiResult {
    let value = TrezorUiEnum::ConfirmValue {
        title: title.into(),
        value: content.into(),
        description: description.map(|d| d.into()),
        is_data,
        subtitle: subtitle.map(|s| s.into()),
        verb: verb.map(|v| v.into()),
        info,
        hold,
        chunkify,
        page_counter,
        cancel,
        br_name: br_name.map(|b| b.into()),
        br_code,
        external_menu,
        warning_footer: warning_footer.map(|w| w.into()),
    };
    info!("confirm_value calling ui call");
    ipc_ui_call(&value)
}

fn confirm_value_intro(
    title: &str,
    content: &str,
    subtitle: Option<&str>,
    verb: Option<&str>,
    verb_cancel: Option<&str>,
    hold: bool,
    chunkify: bool,
    br_name: Option<&str>,
    br_code: i32,
) -> UiResult {
    let value = TrezorUiEnum::ConfirmValueIntro {
        title: title.into(),
        value: content.into(),
        subtitle: subtitle.map(|s| s.into()),
        verb: verb.map(|v| v.into()),
        verb_cancel: verb_cancel.map(|v| v.into()),
        hold,
        chunkify,
        br_name: br_name.map(|b| b.into()),
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
    br_code: i32,
    hold: bool,
    verb: Option<&str>,
    verb_cancel: Option<&str>,
    chunkify: bool,
    ask_pagination: bool,
    is_data: bool,
) -> UiResult {
    if ask_pagination {
        interact_with_info_flow(
            |name| {
                confirm_value_intro(
                    title,
                    &data[..data.len().min(150)], /* TODO: be precise about the 1 st page */
                    description,
                    verb,
                    verb_cancel,
                    hold,
                    chunkify,
                    name,
                    br_code,
                )
            },
            |name| {
                confirm_value(
                    subtitle.unwrap_or(title),
                    data,
                    None,
                    name,
                    br_code,
                    is_data,
                    None,
                    None,
                    false,
                    hold,
                    chunkify,
                    true,
                    true,
                    false,
                    None,
                )
            },
            br_name,
            Some(true),
            Some(true),
        )
    } else {
        confirm_value(
            title,
            data,
            description,
            Some(br_name),
            br_code,
            true,
            verb,
            subtitle,
            false,
            false,
            chunkify,
            false,
            true,
            false,
            None,
        )
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
    br_code: i32,
) -> UiResult {
    let value = TrezorUiEnum::ConfirmSummary {
        title: title.unwrap_or("Send").into(),
        amount: amount.map(|a| a.into()),
        amount_label: amount_label.map(|l| l.into()),
        fee: fee.into(),
        fee_label: fee_label.into(),
        account_title: account_title.map(|t| t.into()),
        account_items: account_items
            .map(|items| PropsList::from_prop_slice(items).map_err(|_| Error::FailedToSend))
            .transpose()?,
        extra_title: extra_title.map(|t| t.into()),
        extra_items: extra_items
            .map(|items| PropsList::from_prop_slice(items).map_err(|_| Error::FailedToSend))
            .transpose()?,
        back_button: back_button,
        br_name: br_name.map(|b| b.into()),
        br_code: br_code,
    };
    ipc_ui_call(&value)
}

pub fn confirm_action(
    title: &str,
    action: &str,
    hold: bool,
    verb: Option<&str>,
    br_name: Option<&str>,
    br_code: i32,
) -> UiResult {
    let value = TrezorUiEnum::ConfirmAction {
        title: title.into(),
        action: action.into(),
        hold,
        verb: verb.map(|v| v.into()),
        br_name: br_name.map(|b| b.into()),
        br_code,
    };
    ipc_ui_call_confirm(&value)
}

pub fn confirm_long_value(title: &str, content: &str, br_code: i32) -> UiResult {
    let value = TrezorUiEnum::ConfirmLong {
        title: title.into(),
        pages: (content.chars().count() + CHARS_PER_PAGE - 1) / CHARS_PER_PAGE,
        br_code,
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

fn select_menu(items: &[&str], cancel: Option<&str>, br_code: i32) -> UiResult {
    let value = TrezorUiEnum::SelectMenu {
        items: StrList::from_str_slice(items).map_err(|_| Error::FailedToSend)?,
        cancel: cancel.map(|c| c.into()),
        br_code,
    };
    match ipc_ui_call(&value) {
        Ok(TrezorUiResult::Integer(idx)) if (idx as usize) < items.len() => {
            Ok(TrezorUiResult::Integer(idx))
        }
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
    br_name: Option<&str>,
    br_code: i32,
) -> UiResult {
    let value = TrezorUiEnum::ConfirmProperties {
        title: title.into(),
        props: PropsList::from_prop_slice(props).map_err(|_| Error::FailedToSend)?,
        subtitle: subtitle.map(|s| s.into()),
        verb: verb.map(|v| v.into()),
        hold,
        br_name: br_name.map(|b| b.into()),
        br_code,
    };
    ipc_ui_call_confirm(&value)
}

pub fn show_properties(
    title: &str,
    props: &[(&str, &str, bool)],
    subtitle: Option<&str>,
    br_name: Option<&str>,
    br_code: i32,
) -> Result<()> {
    let value = TrezorUiEnum::ShowProperties {
        title: title.into(),
        props: PropsList::from_prop_slice(props).map_err(|_| Error::FailedToSend)?,
        subtitle: subtitle.map(|s| s.into()),
        br_name: br_name.map(|b| b.into()),
        br_code,
    };
    ipc_ui_call_void(&value)
}

/// Show a warning message
pub fn show_warning(
    title: &str,
    content: &str,
    verb: &str,
    br_name: Option<&str>,
    br_code: i32,
    allow_cancel: bool,
    danger: bool,
) -> Result<()> {
    let value = TrezorUiEnum::Warning {
        title: title.into(),
        content: content.into(),
        verb: verb.into(),
        br_name: br_name.map(|b| b.into()),
        br_code,
        allow_cancel,
        danger,
    };
    ipc_ui_call_void(&value)
}

pub fn show_info_with_cancel(
    title: &str,
    items: &[(&str, &str, bool)],
    chunkify: bool,
    br_name: Option<&str>,
    br_code: i32,
) -> UiResult {
    let value = TrezorUiEnum::ShowInfoWithCancel {
        title: title.into(),
        items: PropsList::from_prop_slice(items).map_err(|_| Error::FailedToSend)?,
        chunkify,
        br_name: br_name.map(|b| b.into()),
        br_code,
    };
    ipc_ui_call_confirm(&value)
}

/// Show a mismatch message
pub fn show_mismatch(title: &str, br_code: i32) -> UiResult {
    let value = TrezorUiEnum::Mismatch {
        title: title.into(),
        br_code,
    };
    ipc_ui_call_confirm(&value)
}

pub fn confirm_trade(
    title: &str,
    subtitle: &str,
    buy: &str,
    sell: Option<&str>,
    can_go_back: bool,
    br_name: Option<&str>,
    br_code: i32,
) -> UiResult {
    let value = TrezorUiEnum::ConfirmTrade {
        title: title.into(),
        subtitle: subtitle.into(),
        buy: buy.into(),
        sell: sell.map(|s| s.into()),

        back_button: can_go_back,
        br_name: br_name.map(|b| b.into()),
        br_code,
    };
    ipc_ui_call(&value)
}

/// Show a danger message
pub fn show_danger(
    title: &str,
    content: &str,
    br_name: Option<&str>,
    br_code: i32,
    verb_cancel: Option<&str>,
    menu_title: Option<&str>,
) -> UiResult {
    let value = TrezorUiEnum::Danger {
        title: title.into(),
        content: content.into(),
        br_name: br_name.map(|b| b.into()),
        br_code,
        verb_cancel: verb_cancel.map(|v| v.into()),
        menu_title: menu_title.map(|m| m.into()),
    };
    ipc_ui_call_confirm(&value)
}

/// Show a success message
pub fn show_success(
    title: &str,
    content: &str,
    button: &str,
    duration_ms: Option<u32>,
    br_name: Option<&str>,
    br_code: i32,
) -> Result<()> {
    let value = TrezorUiEnum::Success {
        title: title.into(),
        content: content.into(),
        button: button.into(),
        duration_ms,
        br_name: br_name.map(|b| b.into()),
        br_code,
    };
    ipc_ui_call_void(&value)
}

/// Request a number from the user within a range
pub fn request_number(
    title: &str,
    content: &str,
    initial: u32,
    min: u32,
    max: u32,
    br_code: i32,
) -> UiResult {
    let value = TrezorUiEnum::RequestNumber {
        title: title.into(),
        content: content.into(),
        initial,
        min,
        max,
        br_code,
    };

    let result = ipc_ui_call(&value)?;
    match result {
        TrezorUiResult::Integer(_) => Ok(result),
        _ => Ok(TrezorUiResult::Cancelled),
    }
}

pub fn show_public_key(
    key: &str,
    title: &str,
    account: Option<&str>,
    path: Option<&str>,
    warning: Option<&str>,
    br_name: &str,
    br_code: i32,
) -> UiResult {
    let value = TrezorUiEnum::ShowPublicKey {
        pubkey: key.into(),
        title: title.into(),
        account: account.map(|s| s.into()),
        path: path.map(|s| s.into()),
        warning: warning.map(|s| s.into()),
        br_name: br_name.into(),
        br_code,
    };
    ipc_ui_call_confirm(&value)
}

pub fn should_show_more(
    title: &str,
    para: &[(&str, bool)],
    button_text: &str,
    br_name: Option<&str>,
    br_code: i32,
) -> Result<bool> {
    // TODO: move mapping to the coreapp
    match confirm_with_info(title, None, para, "Confirm", button_text, br_name, br_code) {
        Ok(TrezorUiResult::Confirmed) => Ok(false),
        Ok(TrezorUiResult::Info) => Ok(true),
        _ => {
            // TODO: proper error type
            Err(Error::Timeout)
        }
    }
}

pub fn confirm_with_info(
    title: &str,
    subtitle: Option<&str>,
    para: &[(&str, bool)],
    verb: &str,
    verb_info: &str,
    br_name: Option<&str>,
    br_code: i32,
) -> UiResult {
    let value = TrezorUiEnum::ConfirmWithInfo {
        title: title.into(),
        subtitle: subtitle.map(|s| s.into()),
        items: StrExtList::from_str_slice(para).map_err(|_| Error::FailedToSend)?,
        verb: verb.into(),
        verb_info: verb_info.into(),
        br_name: br_name.map(|b| b.into()),
        br_code,
    };
    ipc_ui_call(&value)
}

pub fn show_address(
    address: &str,
    title: Option<&str>,
    subtitle: Option<&str>,
    account: Option<&str>,
    path: Option<&str>,
    xpubs: &[(&str, &str, bool)],
    chunkify: Option<bool>,
    br_code: i32,
) -> UiResult {
    let value = TrezorUiEnum::ShowAddress {
        address: address.into(),
        title: title.map(|s| s.into()),
        subtitle: subtitle.map(|s| s.into()),
        account: account.map(|s| s.into()),
        path: path.map(|s| s.into()),
        xpubs: PropsList::from_prop_slice(xpubs).map_err(|_| Error::FailedToSend)?,
        chunkify,
        br_code,
    };
    ipc_ui_call_confirm(&value)
}
