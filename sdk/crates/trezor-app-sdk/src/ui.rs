//! High-level UI API for interacting with the Trezor display.
//!
//! All functions in this module send an IPC message to the Core firmware task,
//! which renders the requested screen and returns the user's response.
//!
//! ## Examples
//!
//! ```rust
//! use trezor_app_sdk::ui;
//!
//! // Show a confirmation dialog
//! let result = ui::confirm_action("Sign transaction", "Do you want to sign?",
//!     None, None, false, None, true, Some("confirm"), 1, false)?;
//!
//! // Show a list of key-value properties
//! let props = [Property { key: "Amount".into(), value: "1.0 BTC".into(), mono: false }];
//! ui::confirm_properties("Details", &props, None, None, false, Some("confirm"), 1)?;
//!
//! // Show a success screen
//! ui::show_success("Done", "Transaction signed", "Continue", None, Some("success"), 1)?;
//!
//! // Show a progress bar
//! ui::init_progress(Some("Loading..."), Some("Please wait"), false, false)?;
//! ui::update_progress(Some("50%"), 50)?;
//! ui::end_progress()?;
//! ```

pub use rkyv::Archived;
use rkyv::api::low::deserialize;
use rkyv::rancor::Failure;
use rkyv::to_bytes;

use crate::core_services::services_or_die;
use crate::ipc::IpcMessage;
use crate::service::CoreIpcService;
pub use crate::structs::{
    ConfirmAction, ConfirmProperties, ConfirmSummary, ConfirmTrade, ConfirmValue,
    ConfirmValueIntro, ConfirmWithInfo, Property, RequestNumber, SelectMenu, ShowAddress,
    ShowDanger, ShowInfoWithCancel, ShowMismatch, ShowProperties, ShowPublicKey, ShowSuccess,
    ShowWarning, StrExt, TrezorProgressEnum, TrezorUiEnum, TrezorUiResult,
};
use crate::util::Timeout;
use crate::{Error, unwrap};

pub type ArchivedTrezorUiResult = Archived<TrezorUiResult>;
pub type ArchivedTrezorUiEnum<'a> = Archived<TrezorUiEnum<'a>>;

// ============================================================================
// Helper Functions
// ============================================================================

type Result<T> = core::result::Result<T, Error>;
pub type UiResult = Result<TrezorUiResult>;

fn ipc_ui_call(value: &TrezorUiEnum) -> UiResult {
    let bytes = to_bytes::<Failure>(value).map_err(|_| Error::ServiceError)?;

    let message = IpcMessage::new(0, bytes.as_ref());
    let result = services_or_die().call(CoreIpcService::Ui, &message, Timeout::max())?;

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
        Err(e) => Err(e),
    }
}

/// Send a UI call that doesn't expect a meaningful response
fn ipc_ui_call_void(value: &TrezorUiEnum) -> Result<()> {
    ipc_ui_call(value)?;
    Ok(())
}

fn ipc_progress_call(value: &TrezorProgressEnum) -> Result<()> {
    let bytes = to_bytes::<Failure>(value).map_err(|_| Error::ServiceError)?;

    let message = IpcMessage::new(value.id(), bytes.as_ref());
    let _ = services_or_die().call(CoreIpcService::Progress, &message, Timeout::max())?;
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
                return Err(Error::Cancelled);
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
                return Err(Error::Cancelled);
            }
        }
    }
}

pub struct Details<'a> {
    pub name: &'a str,
    pub props: &'a [Property<'a>],
    pub title: Option<&'a str>,
    pub subtitle: Option<&'a str>,
    pub br_code: i32,
}

impl<'a> Details<'a> {
    pub fn new(
        name: &'a str,
        props: &'a [Property<'a>],
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
        show_properties(ShowProperties::new(
            self.title.unwrap_or(self.name),
            self.props,
            self.subtitle,
            None,
            self.br_code,
        ))
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
        // TODO: impl br code
        confirm_action(ConfirmAction::new(
            self.title, "", None, None, false, None, false, None, 1, false,
        ))
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
            return Err(Error::Cancelled);
        }

        let mut items = ["".into(); Self::MAX_MENU_ITEMS];
        let mut i = 0usize;
        while i < self.children.len() {
            items[i] = self.children[i].name.into();
            i += 1;
        }

        loop {
            let choice = select_menu(
                SelectMenu::new(
                    &items[..self.children.len()],
                    self.cancel.as_ref().map(|c| c.title),
                    1,
                ),
                self.children.len(),
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
                            _ => return Err(Error::Cancelled),
                        }
                    }
                }
                // TODO: proper error type
                _ => return Err(Error::Cancelled),
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

pub fn confirm_value<'a>(confirm_value: ConfirmValue<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmValue(confirm_value))
}

pub fn confirm_value_intro<'a>(confirm_value_intro: ConfirmValueIntro<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmValueIntro(confirm_value_intro))
}

pub fn confirm_summary<'a>(confirm_summary: ConfirmSummary<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmSummary(confirm_summary))
}

pub fn confirm_action<'a>(confirm_action: ConfirmAction<'a>) -> UiResult {
    ipc_ui_call_confirm(&TrezorUiEnum::ConfirmAction(confirm_action))
}

fn select_menu<'a>(select_menu: SelectMenu<'a>, len: usize) -> UiResult {
    match ipc_ui_call(&TrezorUiEnum::SelectMenu(select_menu)) {
        Ok(TrezorUiResult::Integer(idx)) if (idx as usize) < len => {
            Ok(TrezorUiResult::Integer(idx))
        }
        Ok(TrezorUiResult::Confirmed) => Ok(TrezorUiResult::Confirmed),
        Ok(_) => Ok(TrezorUiResult::Cancelled),
        Err(e) => Err(e),
    }
}

pub fn confirm_properties<'a>(confirm_properties: ConfirmProperties<'a>) -> UiResult {
    ipc_ui_call_confirm(&TrezorUiEnum::ConfirmProperties(confirm_properties))
}

pub fn show_properties<'a>(show_properties: ShowProperties<'a>) -> Result<()> {
    ipc_ui_call_void(&TrezorUiEnum::ShowProperties(show_properties))
}

pub fn show_warning<'a>(show_warning: ShowWarning<'a>) -> Result<()> {
    ipc_ui_call_void(&TrezorUiEnum::ShowWarning(show_warning))
}

pub fn show_info_with_cancel<'a>(show_info_with_cancel: ShowInfoWithCancel<'a>) -> UiResult {
    ipc_ui_call_confirm(&TrezorUiEnum::ShowInfoWithCancel(show_info_with_cancel))
}

pub fn show_mismatch<'a>(show_mismatch: ShowMismatch<'a>) -> UiResult {
    ipc_ui_call_confirm(&TrezorUiEnum::ShowMismatch(show_mismatch))
}

pub fn confirm_trade<'a>(confirm_trade: ConfirmTrade<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmTrade(confirm_trade))
}

pub fn show_danger<'a>(show_danger: ShowDanger<'a>) -> UiResult {
    ipc_ui_call_confirm(&TrezorUiEnum::ShowDanger(show_danger))
}

pub fn show_success<'a>(show_success: ShowSuccess<'a>) -> Result<()> {
    ipc_ui_call_void(&TrezorUiEnum::ShowSuccess(show_success))
}

pub fn request_number<'a>(request_number: RequestNumber<'a>) -> UiResult {
    match ipc_ui_call(&TrezorUiEnum::RequestNumber(request_number))? {
        result @ TrezorUiResult::Integer(_) => Ok(result),
        _ => Ok(TrezorUiResult::Cancelled),
    }
}

pub fn show_public_key<'a>(show_public_key: ShowPublicKey<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ShowPublicKey(show_public_key))
}

pub fn confirm_with_info<'a>(confirm_with_info: ConfirmWithInfo<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmWithInfo(confirm_with_info))
}

pub fn show_address<'a>(show_address: ShowAddress<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ShowAddress(show_address))
}

pub fn should_show_more<'a>(
    title: &'a str,
    para: &'a [StrExt<'a>],
    button_text: &'a str,
    br_name: Option<&'a str>,
    br_code: i32,
    verb: &'a str,
) -> Result<bool> {
    match confirm_with_info(ConfirmWithInfo::new(
        title,
        None,
        para,
        verb,
        Some(button_text),
        br_name,
        br_code,
    )) {
        Ok(TrezorUiResult::Confirmed) => Ok(false),
        Ok(TrezorUiResult::Info) => Ok(true),
        _ => Err(Error::Cancelled),
    }
}
