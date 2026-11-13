//! Stable-ABI mirror of `structs.rs`'s UI/progress argument structs.
//!
//! `structs.rs` is the wire IDL shared byte-for-byte with Core's Rust+Python
//! side and isn't itself ABI-stable (`rkyv`-only, not `#[stabby::stabby]`).
//! These mirror types exist purely so the `UiV1` trait can cross the stable
//! ABI boundary; `core/embed/api`'s implementation converts a mirror value
//! into the matching `structs.rs` enum internally before sending it over the
//! wire.
//!
//! Optional string fields are `StabbyOption<Slice<u8>>` (raw bytes), not
//! `StabbyOption<Str>` — `Str` doesn't propagate niche/determinant info
//! through its own `Slice<u8>` wrapper, so `stabby::option::Option<Str<'_>>`
//! fails to satisfy `#[stabby::stabby]`'s `IDeterminantProvider` bound where
//! `Option<Slice<u8>>` (the type `Str` itself wraps) does not have this
//! issue. `opt_bytes`/[`as_opt_str`] convert at the edges.

use stabby::option::Option as StabbyOption;
use stabby::slice::Slice;
use stabby::str::Str;

use super::util::ServiceResult;

// the app-side constructors are in `crate::ui`

/// Recovers the `&str` an `opt_bytes`-produced field holds, if any.
///
/// # Safety
///
/// `bytes`, if present, must have come from `opt_bytes` applied to a
/// genuine `&str` (true for every field on every type in this module).
pub fn as_opt_str(bytes: StabbyOption<Slice<'_, u8>>) -> Option<&str> {
    core::option::Option::from(bytes).map(|b: Slice<'_, u8>| {
        // SAFETY: see function doc.
        unsafe { core::str::from_utf8_unchecked(b.as_slice()) }
    })
}

/// A key-value pair with an optional monospace flag, used in UI detail views.
#[stabby::stabby]
#[derive(Clone)]
pub struct Property<'a> {
    /// Name of the property.
    pub key: Str<'a>,
    /// Value of the property.
    pub value: Str<'a>,
    /// Shown in a monospace font.
    pub mono: bool,
}

/// A string with an optional monospace flag, used in UI list views.
#[stabby::stabby]
#[derive(Clone)]
pub struct StrExt<'a> {
    /// The text.
    pub key: Str<'a>,
    /// Shown in a monospace font.
    pub mono: bool,
}

/// Result returned by Core after a UI interaction.
#[stabby::stabby]
#[repr(C, u8)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum TrezorUiResult {
    /// The user confirmed.
    Confirmed,
    /// The user went back.
    Back,
    /// The user cancelled.
    Cancelled,
    /// The user asked for more information.
    Info,
    /// The number the user entered.
    Integer(u32),
}

/// A menu of selectable string items.
#[stabby::stabby]
#[derive(Clone)]
pub struct SelectMenu<'a> {
    /// Entries shown on the screen.
    pub items: Slice<'a, Str<'a>>,
    /// Label of the cancel entry, if any.
    pub cancel: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

/// Stable-ABI form of [`crate::structs::ConfirmTrade`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmTrade<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// Subtitle under the title.
    pub subtitle: Str<'a>,
    /// What the user gets.
    pub buy: Str<'a>,
    /// What the user gives.
    pub sell: StabbyOption<Slice<'a, u8>>,
    /// The left button returns `Back` instead of cancelling.
    pub back_button: bool,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

/// Stable-ABI form of [`crate::structs::ConfirmAction`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmAction<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// The action to confirm.
    pub action: Str<'a>,
    /// Description text.
    pub description: StabbyOption<Slice<'a, u8>>,
    /// Subtitle under the title.
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    /// The user confirms by holding the button.
    pub hold: bool,
    /// Shows a cancel button.
    pub cancel: bool,
    /// Text of the confirm button.
    pub verb: StabbyOption<Slice<'a, u8>>,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// The menu button returns `Info` to the app instead of opening Core's menu.
    pub external_menu: bool,
}

/// Stable-ABI form of [`crate::structs::ConfirmSummary`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmSummary<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// The amount.
    pub amount: StabbyOption<Slice<'a, u8>>,
    /// Label of the amount.
    pub amount_label: StabbyOption<Slice<'a, u8>>,
    /// The fee.
    pub fee: Str<'a>,
    /// Label of the fee.
    pub fee_label: Str<'a>,
    /// Title of the account information.
    pub account_title: StabbyOption<Slice<'a, u8>>,
    /// Account information as key-value pairs.
    pub account_items: StabbyOption<Slice<'a, Property<'a>>>,
    /// Title of the extra information.
    pub extra_title: StabbyOption<Slice<'a, u8>>,
    /// Extra information as key-value pairs.
    pub extra_items: StabbyOption<Slice<'a, Property<'a>>>,
    /// The left button returns `Back` instead of cancelling.
    pub back_button: bool,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

/// Fields mirror [`crate::structs::ConfirmValue`] except `footer`, which is
/// flattened into `footer_text`/`footer_bold` since stabby has no tuples;
/// [`Self::new`] still takes the same `Option<(&str, bool)>` shape as the
/// wire-format constructor, since a plain (non-ABI-crossing) parameter can
/// be a tuple.
#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmValue<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// The value to confirm.
    pub value: Str<'a>,
    /// Description text.
    pub description: StabbyOption<Slice<'a, u8>>,
    /// The value is data, shown in a data font.
    pub is_data: bool,
    /// Subtitle under the title.
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    /// Text of the confirm button.
    pub verb: StabbyOption<Slice<'a, u8>>,
    /// Shows an info button in the header.
    pub info: bool,
    /// The user confirms by holding the button.
    pub hold: bool,
    /// Shows the value in monospace chunks, for easier comparison.
    pub chunkify: bool,
    /// Shows a page counter.
    pub page_counter: bool,
    /// Shows a cancel button.
    pub cancel: bool,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// The menu button returns `Info` to the app instead of opening Core's menu.
    pub external_menu: bool,
    /// Footer text.
    pub footer_text: StabbyOption<Slice<'a, u8>>,
    /// Shows the footer text in bold.
    pub footer_bold: bool,
}

/// Stable-ABI form of [`crate::structs::ConfirmValueIntro`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmValueIntro<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// The value to confirm.
    pub value: Str<'a>,
    /// Subtitle under the title.
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    /// Text of the confirm button.
    pub verb: StabbyOption<Slice<'a, u8>>,
    /// Text of the cancel button.
    pub verb_cancel: StabbyOption<Slice<'a, u8>>,
    /// Text of the button that shows the whole value.
    pub verb_view_all: StabbyOption<Slice<'a, u8>>,
    /// The user confirms by holding the button.
    pub hold: bool,
    /// Shows the value in monospace chunks, for easier comparison.
    pub chunkify: bool,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

/// Stable-ABI form of [`crate::structs::ShowWarning`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ShowWarning<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// Body text.
    pub content: Str<'a>,
    /// Text of the confirm button.
    pub verb: Str<'a>,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// Lets the user cancel.
    pub allow_cancel: bool,
    /// Shows the screen as dangerous.
    pub danger: bool,
}

/// Stable-ABI form of [`crate::structs::ShowMismatch`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ShowMismatch<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

/// Stable-ABI form of [`crate::structs::ShowDanger`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ShowDanger<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// Body text.
    pub content: Str<'a>,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// Text of the cancel button.
    pub verb_cancel: StabbyOption<Slice<'a, u8>>,
    /// Title of the menu.
    pub menu_title: StabbyOption<Slice<'a, u8>>,
}

/// Stable-ABI form of [`crate::structs::ShowSuccess`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ShowSuccess<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// Body text.
    pub content: Str<'a>,
    /// Text of the button.
    pub button: Str<'a>,
    /// Closes the screen after this many milliseconds.
    pub duration_ms: StabbyOption<u32>,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

/// Stable-ABI form of [`crate::structs::RequestNumber`].
#[stabby::stabby]
#[derive(Clone)]
pub struct RequestNumber<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// Body text.
    pub content: Str<'a>,
    /// Number shown at first.
    pub initial: u32,
    /// Smallest allowed number.
    pub min: u32,
    /// Largest allowed number.
    pub max: u32,
    /// Button request code sent to the host.
    pub br_code: i32,
}

/// Stable-ABI form of [`crate::structs::ConfirmProperties`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmProperties<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// Properties shown as key-value pairs.
    pub props: Slice<'a, Property<'a>>,
    /// Subtitle under the title.
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    /// Text of the confirm button.
    pub verb: StabbyOption<Slice<'a, u8>>,
    /// The user confirms by holding the button.
    pub hold: bool,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// The menu button returns `Info` to the app instead of opening Core's menu.
    pub external_menu: bool,
}

/// Stable-ABI form of [`crate::structs::ShowProperties`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ShowProperties<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// Properties shown as key-value pairs.
    pub props: Slice<'a, Property<'a>>,
    /// Subtitle under the title.
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

/// Stable-ABI form of [`crate::structs::ShowPublicKey`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ShowPublicKey<'a> {
    /// The public key.
    pub pubkey: Str<'a>,
    /// Screen title.
    pub title: Str<'a>,
    /// Account name shown with the key.
    pub account: StabbyOption<Slice<'a, u8>>,
    /// Derivation path shown with the key.
    pub path: StabbyOption<Slice<'a, u8>>,
    /// Warning text.
    pub warning: StabbyOption<Slice<'a, u8>>,
    /// Button request name sent to the host.
    pub br_name: Str<'a>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

/// Stable-ABI form of [`crate::structs::ShowInfoWithCancel`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ShowInfoWithCancel<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// Entries shown on the screen.
    pub items: Slice<'a, Property<'a>>,
    /// Shows the value in monospace chunks, for easier comparison.
    pub chunkify: bool,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

/// Stable-ABI form of [`crate::structs::ConfirmWithInfo`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmWithInfo<'a> {
    /// Screen title.
    pub title: Str<'a>,
    /// Subtitle under the title.
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    /// Entries shown on the screen.
    pub items: Slice<'a, StrExt<'a>>,
    /// Text of the confirm button.
    pub verb: Str<'a>,
    /// Text of the info button.
    pub verb_info: StabbyOption<Slice<'a, u8>>,
    /// Button request name sent to the host.
    pub br_name: StabbyOption<Slice<'a, u8>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

/// Stable-ABI form of [`crate::structs::ShowAddress`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ShowAddress<'a> {
    /// The address.
    pub address: Str<'a>,
    /// The address as encoded in the QR code.
    pub address_qr: Str<'a>,
    /// Screen title.
    pub title: StabbyOption<Slice<'a, u8>>,
    /// Subtitle under the title.
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    /// Account name shown with the address.
    pub account: StabbyOption<Slice<'a, u8>>,
    /// Derivation path shown with the address.
    pub path: StabbyOption<Slice<'a, u8>>,
    /// Extended public keys of a multisig address.
    pub xpubs: Slice<'a, Property<'a>>,
    /// Shows the value in monospace chunks, for easier comparison.
    pub chunkify: bool,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// The address is case-sensitive.
    pub case_sensitive: bool,
}

/// Talks to Core's UI/progress screens. Each method sends one screen request
/// over the wire and returns Core's response — implemented in `core/embed/api`
/// against [`super::wire::WireV1`].
#[stabby::stabby(checked)]
pub trait UiV1: Send + Sync {
    /// Shows a [`ConfirmValue`] screen.
    extern "C" fn confirm_value<'a>(
        &self,
        value: ConfirmValue<'a>,
    ) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ConfirmValueIntro`] screen.
    extern "C" fn confirm_value_intro<'a>(
        &self,
        value: ConfirmValueIntro<'a>,
    ) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ConfirmSummary`] screen.
    extern "C" fn confirm_summary<'a>(
        &self,
        value: ConfirmSummary<'a>,
    ) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ConfirmAction`] screen.
    extern "C" fn confirm_action<'a>(
        &self,
        value: ConfirmAction<'a>,
    ) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`SelectMenu`] screen.
    extern "C" fn select_menu<'a>(&self, value: SelectMenu<'a>) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ConfirmProperties`] screen.
    extern "C" fn confirm_properties<'a>(
        &self,
        value: ConfirmProperties<'a>,
    ) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ShowProperties`] screen.
    extern "C" fn show_properties<'a>(&self, value: ShowProperties<'a>) -> ServiceResult<()>;

    /// Shows a [`ShowWarning`] screen.
    extern "C" fn show_warning<'a>(&self, value: ShowWarning<'a>) -> ServiceResult<()>;

    /// Shows a [`ShowInfoWithCancel`] screen.
    extern "C" fn show_info_with_cancel<'a>(
        &self,
        value: ShowInfoWithCancel<'a>,
    ) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ShowMismatch`] screen.
    extern "C" fn show_mismatch<'a>(
        &self,
        value: ShowMismatch<'a>,
    ) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ConfirmTrade`] screen.
    extern "C" fn confirm_trade<'a>(
        &self,
        value: ConfirmTrade<'a>,
    ) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ShowDanger`] screen.
    extern "C" fn show_danger<'a>(&self, value: ShowDanger<'a>) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ShowSuccess`] screen.
    extern "C" fn show_success<'a>(&self, value: ShowSuccess<'a>) -> ServiceResult<()>;

    /// Shows a [`RequestNumber`] screen.
    extern "C" fn request_number<'a>(
        &self,
        value: RequestNumber<'a>,
    ) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ShowPublicKey`] screen.
    extern "C" fn show_public_key<'a>(
        &self,
        value: ShowPublicKey<'a>,
    ) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ConfirmWithInfo`] screen.
    extern "C" fn confirm_with_info<'a>(
        &self,
        value: ConfirmWithInfo<'a>,
    ) -> ServiceResult<TrezorUiResult>;

    /// Shows a [`ShowAddress`] screen.
    extern "C" fn show_address<'a>(&self, value: ShowAddress<'a>) -> ServiceResult<TrezorUiResult>;

    /// Shows a progress indicator with an optional `description` and `title`.
    extern "C" fn init_progress<'a>(
        &self,
        description: StabbyOption<Slice<'a, u8>>,
        title: StabbyOption<Slice<'a, u8>>,
        indeterminate: bool,
        danger: bool,
    ) -> ServiceResult<()>;

    /// Updates the progress indicator's `description` and `value` (0 to 1000).
    extern "C" fn update_progress<'a>(
        &self,
        description: StabbyOption<Slice<'a, u8>>,
        value: u32,
    ) -> ServiceResult<()>;

    /// Closes the progress indicator.
    extern "C" fn end_progress(&self) -> ServiceResult<()>;
}

/// The stabby vtable of [`UiV1`].
pub type UiV1Vtable = stabby::vtable!(UiV1 + Send + Sync);
/// A borrowed `dyn UiV1`.
pub type UiV1Ref<'a> = stabby::DynRef<'a, UiV1Vtable>;
/// A `dyn UiV1` that lives as long as the app.
pub type StaticUiV1 = UiV1Ref<'static>;
