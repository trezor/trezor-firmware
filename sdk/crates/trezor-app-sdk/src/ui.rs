//! High-level UI API for interacting with the Trezor display.
//!
//! All functions in this module send an IPC message to the Core firmware task,
//! which renders the requested screen and returns the user's response.
//!
//! ## Examples
//!
//! ```no_run
//! use trezor_app_sdk::ui::{self, ConfirmAction, ConfirmProperties, Property, ShowSuccess};
//!
//! # Ok::<(), trezor_app_sdk::Error>(())
//! ```

use rkyv::api::low::deserialize;
use rkyv::rancor::Failure;
use rkyv::{Archived, to_bytes};

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

// pub type ArchivedTrezorUiResult = Archived<TrezorUiResult>;
// pub type ArchivedTrezorUiEnum<'a> = Archived<TrezorUiEnum<'a>>;

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
    let archived = unwrap!(rkyv::access::<Archived<TrezorUiResult>, Failure>(
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

/// Initializes a progress screen.
///
/// Must be called before [`update_progress`] and [`end_progress`].
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui;
/// ui::init_progress(Some("Signing..."), Some("Please wait"), false, false)?;
/// ui::update_progress(None, 50)?;
/// ui::end_progress()?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
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

/// Updates the progress bar value and optionally the description text.
///
/// Must be called after [`init_progress`].
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui;
/// ui::init_progress(Some("Working..."), None, false, false)?;
/// ui::update_progress(Some("50% done"), 50)?;
/// ui::update_progress(Some("Almost done"), 90)?;
/// ui::end_progress()?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn update_progress(description: Option<&str>, value: u32) -> Result<()> {
    let value = TrezorProgressEnum::Update {
        description: description.map(|d| d.into()),
        value,
    };
    ipc_progress_call(&value)
}

/// Ends and dismisses the progress screen.
///
/// Must be called after [`init_progress`] to clean up the progress display.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui;
/// ui::init_progress(None, None, false, false)?;
/// ui::update_progress(None, 100)?;
/// ui::end_progress()?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn end_progress() -> Result<()> {
    let value = TrezorProgressEnum::End;
    ipc_progress_call(&value)
}

/// Runs a sequence of confirmation screens in order, supporting back navigation.
///
/// - Each factory in `confirm_factories` is called in order.
/// - [`TrezorUiResult::Confirmed`] advances to the next step.
/// - [`TrezorUiResult::Back`] returns to the previous step (if any).
/// - [`TrezorUiResult::Cancelled`] aborts the whole flow.
///
/// Returns [`TrezorUiResult::Confirmed`] when all steps are confirmed.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ConfirmAction};
///
/// ui::confirm_linear_flow(&[
///     &|| ui::confirm_action(ConfirmAction::new("Step 1", "First item", None, None, false, None, false, Some("step1"), 1, false)),
///     &|| ui::confirm_action(ConfirmAction::new("Step 2", "Second item", None, None, false, None, false, None, 1, false)),
/// ])?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
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

/// Converts a [`TrezorUiResult`] into `Ok(())` if confirmed, or [`Error::Cancelled`] otherwise.
///
/// Useful as the outermost check after a UI flow.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ConfirmAction};
///
/// ui::error_if_not_confirmed(
///     ui::confirm_action(ConfirmAction::new("Sign", "Proceed?", None, None, false, None, false, Some("confirm"), 1, false))?
/// )?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn error_if_not_confirmed(result: TrezorUiResult) -> core::result::Result<(), crate::Error> {
    if matches!(result, TrezorUiResult::Confirmed) {
        Ok(())
    } else {
        Err(crate::Error::Cancelled)
    }
}

/// Runs a main layout paired with an optional info layout, looping until confirmed or cancelled.
///
/// - The main layout is called repeatedly until it returns [`TrezorUiResult::Confirmed`] or
///   [`TrezorUiResult::Cancelled`].
/// - If the main layout returns [`TrezorUiResult::Info`], the info layout is opened.
/// - If `info_layout_can_confirm` is `true` and the info layout returns
///   [`TrezorUiResult::Confirmed`], the whole flow is confirmed.
/// - `br_name` is sent on the first call; subsequent calls use `None` unless
///   `repeat_button_request` is `true`.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ConfirmAction, ConfirmProperties, Property};
///
/// let props = [Property::plain("Amount", "1 BTC")];
/// ui::interact_with_info_flow(
///     |br| ui::confirm_action(ConfirmAction::new("Sign", "Proceed?", None, None, false, None, false, br, 1, false)),
///     |br| ui::confirm_properties(ConfirmProperties::new("Details", &props, None, None, false, br, 1)),
///     "confirm_sign",
///     None,
///     None,
/// )?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
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

/// One entry in a [`Menu`], rendered as a [`ShowProperties`] screen when selected.
///
/// No `uDebug` impl: unlike the wire-format types in `structs.rs`, this holds
/// plain `&str` fields (not [`crate::structs::StrSlice`]), and ufmt doesn't
/// implement `uDebug` for `str`/`&str`.
#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Details<'a> {
    name: &'a str,
    props: &'a [Property<'a>],
    title: Option<&'a str>,
    subtitle: Option<&'a str>,
    br_code: i32,
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

/// The cancel entry of a [`Menu`], rendered as a [`ConfirmAction`] screen when selected.
///
/// No `uDebug` impl: see [`Details`] — holds a plain `&str`, which ufmt
/// doesn't implement `uDebug` for.
#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Cancel<'a> {
    title: &'a str,
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

/// A menu of [`Details`] entries plus an optional [`Cancel`] entry, driven by
/// [`Menu::interact`].
///
/// No `uDebug` impl: see [`Details`].
#[derive(Copy, Clone, PartialEq, Eq)]
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
                    self.children[idx as usize].interact()?;
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

/// Runs a main UI layout in a loop, opening a [`Menu`] when the user requests more info.
///
/// - The main layout is called repeatedly until it returns [`TrezorUiResult::Confirmed`] or
///   [`TrezorUiResult::Cancelled`].
/// - If the main layout returns [`TrezorUiResult::Info`], the menu is opened.
///   - If the menu returns [`TrezorUiResult::Cancelled`] (user cancelled from menu), the whole
///     flow is cancelled.
///   - Otherwise the main layout is shown again.
/// - `br_name` is passed only on the first call to the main layout (button request sent once).
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ConfirmValue, Details, Menu, Property};
///
/// let props = [
///     Property::mono("From", "0xDEAD...BEEF"),
///     Property::mono("To", "0xCAFE...BABE"),
/// ];
/// let details = [Details::new("Details", &props, None, None, 1)];
/// let menu = Menu::new(&details, None);
///
/// ui::error_if_not_confirmed(ui::interact_with_menu_flow(
///     |br_name| {
///         ui::confirm_value(ConfirmValue::new(
///             "Sign transaction", "1.5 ETH", Some("Amount"),
///             br_name, 1, false, Some("Sign"), None,
///             false, false, false, false, false, true, None,
///         ))
///     },
///     &menu,
///     Some("confirm_output"),
/// )?)?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
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

/// Shows a value confirmation screen.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ConfirmValue};
/// ui::confirm_value(ConfirmValue::new(
///     "Amount", "1.5 ETH", Some("ETH"), Some("confirm"), 1,
///     false, Some("Confirm"), None, false, false, false, false, false, false, None,
/// ))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn confirm_value<'a>(confirm_value: ConfirmValue<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmValue(confirm_value))
}

/// Shows an introductory value confirmation screen.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ConfirmValueIntro};
/// ui::confirm_value_intro(ConfirmValueIntro::new(
///     "Send ETH", "You are about to send", Some("confirm"), None, None, None, false, false, None, 1,
/// ))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn confirm_value_intro<'a>(confirm_value_intro: ConfirmValueIntro<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmValueIntro(confirm_value_intro))
}

/// Shows a summary confirmation screen, typically at the end of a multi-step flow.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ConfirmSummary};
/// ui::confirm_summary(ConfirmSummary::new(
///     "Summary", None, None, "Total: 1.5 ETH", "Send", None, None, Some("confirm"), None, false, None, 1,
/// ))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn confirm_summary<'a>(confirm_summary: ConfirmSummary<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmSummary(confirm_summary))
}

/// Shows a generic action confirmation dialog.
///
/// Returns [`TrezorUiResult::Confirmed`] or [`TrezorUiResult::Cancelled`].
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ConfirmAction};
/// ui::confirm_action(ConfirmAction::new(
///     "Delete", "Are you sure?", None, None, false, None, false, Some("confirm_delete"), 1, false,
/// ))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn confirm_action<'a>(confirm_action: ConfirmAction<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmAction(confirm_action))
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

/// Shows a list of key-value properties for user confirmation.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ConfirmProperties, Property};
/// let props = [
///     Property::mono("Recipient", "0xDEAD...BEEF"),
///     Property::plain("Amount", "1.5 ETH"),
/// ];
/// ui::confirm_properties(ConfirmProperties::new("Transaction", &props, None, None, false, Some("confirm"), 1))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn confirm_properties<'a>(confirm_properties: ConfirmProperties<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmProperties(confirm_properties))
}

/// Shows a read-only list of key-value properties (no confirmation required).
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ShowProperties, Property};
/// let props = [Property::plain("Version", "1.0.0")];
/// ui::show_properties(ShowProperties::new("About", &props, None, None, 1))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn show_properties<'a>(show_properties: ShowProperties<'a>) -> Result<()> {
    ipc_ui_call_void(&TrezorUiEnum::ShowProperties(show_properties))
}

/// Shows a warning screen (no confirmation, fire-and-forget).
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ShowWarning};
/// ui::show_warning(ShowWarning::new("Warning", "This action is irreversible", "Continue", None, 1, false, false))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn show_warning<'a>(show_warning: ShowWarning<'a>) -> Result<()> {
    ipc_ui_call_void(&TrezorUiEnum::ShowWarning(show_warning))
}

/// Shows an info screen with a cancel button.
///
/// Returns [`TrezorUiResult::Confirmed`] if the user proceeds, [`TrezorUiResult::Cancelled`]
/// if the user cancels.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ShowInfoWithCancel, Property};
/// let props: &[Property] = &[];
/// ui::show_info_with_cancel(ShowInfoWithCancel::new("Info", props, false, Some("confirm"), 1))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn show_info_with_cancel<'a>(show_info_with_cancel: ShowInfoWithCancel<'a>) -> UiResult {
    ipc_ui_call_confirm(&TrezorUiEnum::ShowInfoWithCancel(show_info_with_cancel))
}

/// Shows a mismatch warning screen (e.g. address mismatch).
///
/// Returns [`TrezorUiResult::Confirmed`] if the user acknowledges,
/// [`TrezorUiResult::Cancelled`] otherwise.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ShowMismatch};
/// ui::show_mismatch(ShowMismatch::new("Address mismatch", 1))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn show_mismatch<'a>(show_mismatch: ShowMismatch<'a>) -> UiResult {
    ipc_ui_call_confirm(&TrezorUiEnum::ShowMismatch(show_mismatch))
}

/// Shows a trade confirmation screen (swap / exchange).
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ConfirmTrade};
/// ui::confirm_trade(ConfirmTrade::new("Swap", "1 BTC", "15 ETH", None, false, Some("confirm"), 1))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn confirm_trade<'a>(confirm_trade: ConfirmTrade<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmTrade(confirm_trade))
}

/// Shows a danger warning screen that requires explicit user confirmation.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ShowDanger};
/// ui::show_danger(ShowDanger::new("Danger", "Wipe device?", Some("confirm_wipe"), 1, None, None))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn show_danger<'a>(show_danger: ShowDanger<'a>) -> UiResult {
    ipc_ui_call_confirm(&TrezorUiEnum::ShowDanger(show_danger))
}

/// Shows a success screen (no confirmation required).
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ShowSuccess};
/// ui::show_success(ShowSuccess::new("Done", "Transaction signed", "Continue", None, Some("success"), 1))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn show_success<'a>(show_success: ShowSuccess<'a>) -> Result<()> {
    ipc_ui_call_void(&TrezorUiEnum::ShowSuccess(show_success))
}

/// Shows a numeric input screen and returns the chosen number.
///
/// Returns [`TrezorUiResult::Integer`] with the selected value, or
/// [`TrezorUiResult::Cancelled`] if the user cancels.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, RequestNumber, TrezorUiResult};
/// let res = ui::request_number(RequestNumber::new("Count", "items", 1, 10, 1, 1))?;
/// if let TrezorUiResult::Integer(n) = res {
///     // use n
/// }
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn request_number<'a>(request_number: RequestNumber<'a>) -> UiResult {
    match ipc_ui_call(&TrezorUiEnum::RequestNumber(request_number))? {
        result @ TrezorUiResult::Integer(_) => Ok(result),
        _ => Ok(TrezorUiResult::Cancelled),
    }
}

/// Shows a public key screen for user verification.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ShowPublicKey};
/// ui::show_public_key(ShowPublicKey::new("Public Key", "xpub6CUGRUo...", None, Some("show_pubkey"), None, "xpub", 1))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn show_public_key<'a>(show_public_key: ShowPublicKey<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ShowPublicKey(show_public_key))
}

/// Shows a confirmation screen with an additional info button.
///
/// Returns [`TrezorUiResult::Confirmed`], [`TrezorUiResult::Info`], or
/// [`TrezorUiResult::Cancelled`].
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ConfirmWithInfo, StrExt};
/// let para = [StrExt::plain("Send 1 BTC to 0xDEAD...BEEF")];
/// ui::confirm_with_info(ConfirmWithInfo::new("Sign", None, &para, "Confirm", Some("Details"), Some("confirm"), 1))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn confirm_with_info<'a>(confirm_with_info: ConfirmWithInfo<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ConfirmWithInfo(confirm_with_info))
}

/// Shows an address verification screen.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, ShowAddress, Property};
/// let props: &[Property] = &[];
/// ui::show_address(ShowAddress::new("Receive", "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", None, None, None, Some("show_addr"), props, false, 1, false))?;
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
pub fn show_address<'a>(show_address: ShowAddress<'a>) -> UiResult {
    ipc_ui_call(&TrezorUiEnum::ShowAddress(show_address))
}

/// Shows a paginated text screen and returns whether the user wants to see more.
///
/// Returns `true` if the user pressed the "more info" button, `false` if they confirmed,
/// or [`Error::Cancelled`] if they cancelled.
///
/// ## Example
///
/// ```no_run
/// use trezor_app_sdk::ui::{self, StrExt};
/// let para = [StrExt::plain("This is a long message that may need expansion.")];
/// let show_more = ui::should_show_more("Message", &para, "Show more", Some("confirm"), 1, "Confirm")?;
/// if show_more {
///     // display full details
/// }
/// # Ok::<(), trezor_app_sdk::Error>(())
/// ```
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
