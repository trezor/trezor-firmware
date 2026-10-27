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

use super::util::FastResult;
use super::wire::WireError;

// constructors of the structs below, and the `Option` field helpers
mod constructors;

pub use constructors::as_opt_str;
pub(crate) use constructors::opt_bytes;

/// A key-value pair with an optional monospace flag, used in UI detail views.
#[stabby::stabby]
#[derive(Clone)]
pub struct Property<'a> {
    pub key: Str<'a>,
    pub value: Str<'a>,
    pub mono: bool,
}

/// A string with an optional monospace flag, used in UI list views.
#[stabby::stabby]
#[derive(Clone)]
pub struct StrExt<'a> {
    pub key: Str<'a>,
    pub mono: bool,
}

/// Result returned by Core after a UI interaction.
#[stabby::stabby]
#[repr(C, u8)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum TrezorUiResult {
    Confirmed,
    Back,
    Cancelled,
    Info,
    Integer(u32),
}

/// A menu of selectable string items.
#[stabby::stabby]
#[derive(Clone)]
pub struct SelectMenu<'a> {
    pub items: Slice<'a, Str<'a>>,
    pub cancel: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmTrade<'a> {
    pub title: Str<'a>,
    pub subtitle: Str<'a>,
    pub buy: Str<'a>,
    pub sell: StabbyOption<Slice<'a, u8>>,
    pub back_button: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmAction<'a> {
    pub title: Str<'a>,
    pub action: Str<'a>,
    pub description: StabbyOption<Slice<'a, u8>>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub hold: bool,
    pub cancel: bool,
    pub verb: StabbyOption<Slice<'a, u8>>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
    pub external_menu: bool,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmSummary<'a> {
    pub title: Str<'a>,
    pub amount: StabbyOption<Slice<'a, u8>>,
    pub amount_label: StabbyOption<Slice<'a, u8>>,
    pub fee: Str<'a>,
    pub fee_label: Str<'a>,
    pub account_title: StabbyOption<Slice<'a, u8>>,
    pub account_items: StabbyOption<Slice<'a, Property<'a>>>,
    pub extra_title: StabbyOption<Slice<'a, u8>>,
    pub extra_items: StabbyOption<Slice<'a, Property<'a>>>,
    pub back_button: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
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
    pub title: Str<'a>,
    pub value: Str<'a>,
    pub description: StabbyOption<Slice<'a, u8>>,
    pub is_data: bool,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub verb: StabbyOption<Slice<'a, u8>>,
    pub info: bool,
    pub hold: bool,
    pub chunkify: bool,
    pub page_counter: bool,
    pub cancel: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
    pub external_menu: bool,
    pub footer_text: StabbyOption<Slice<'a, u8>>,
    pub footer_bold: bool,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmValueIntro<'a> {
    pub title: Str<'a>,
    pub value: Str<'a>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub verb: StabbyOption<Slice<'a, u8>>,
    pub verb_cancel: StabbyOption<Slice<'a, u8>>,
    pub verb_view_all: StabbyOption<Slice<'a, u8>>,
    pub hold: bool,
    pub chunkify: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowWarning<'a> {
    pub title: Str<'a>,
    pub content: Str<'a>,
    pub verb: Str<'a>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
    pub allow_cancel: bool,
    pub danger: bool,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowMismatch<'a> {
    pub title: Str<'a>,
    pub br_code: i32,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowDanger<'a> {
    pub title: Str<'a>,
    pub content: Str<'a>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
    pub verb_cancel: StabbyOption<Slice<'a, u8>>,
    pub menu_title: StabbyOption<Slice<'a, u8>>,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowSuccess<'a> {
    pub title: Str<'a>,
    pub content: Str<'a>,
    pub button: Str<'a>,
    pub duration_ms: StabbyOption<u32>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct RequestNumber<'a> {
    pub title: Str<'a>,
    pub content: Str<'a>,
    pub initial: u32,
    pub min: u32,
    pub max: u32,
    pub br_code: i32,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmProperties<'a> {
    pub title: Str<'a>,
    pub props: Slice<'a, Property<'a>>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub verb: StabbyOption<Slice<'a, u8>>,
    pub hold: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowProperties<'a> {
    pub title: Str<'a>,
    pub props: Slice<'a, Property<'a>>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowPublicKey<'a> {
    pub pubkey: Str<'a>,
    pub title: Str<'a>,
    pub account: StabbyOption<Slice<'a, u8>>,
    pub path: StabbyOption<Slice<'a, u8>>,
    pub warning: StabbyOption<Slice<'a, u8>>,
    pub br_name: Str<'a>,
    pub br_code: i32,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowInfoWithCancel<'a> {
    pub title: Str<'a>,
    pub items: Slice<'a, Property<'a>>,
    pub chunkify: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmWithInfo<'a> {
    pub title: Str<'a>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub items: Slice<'a, StrExt<'a>>,
    pub verb: Str<'a>,
    pub verb_info: StabbyOption<Slice<'a, u8>>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowAddress<'a> {
    pub address: Str<'a>,
    pub address_qr: Str<'a>,
    pub title: StabbyOption<Slice<'a, u8>>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub account: StabbyOption<Slice<'a, u8>>,
    pub path: StabbyOption<Slice<'a, u8>>,
    pub xpubs: Slice<'a, Property<'a>>,
    pub chunkify: bool,
    pub br_code: i32,
    pub case_sensitive: bool,
}

/// Talks to Core's UI/progress screens. Each method sends one screen request
/// over the wire and returns Core's response — implemented in `core/embed/api`
/// against [`super::wire::WireV1`].
#[stabby::stabby(checked)]
pub trait UiV1: Send + Sync {
    extern "C" fn confirm_value<'a>(
        &self,
        value: ConfirmValue<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_value_intro<'a>(
        &self,
        value: ConfirmValueIntro<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_summary<'a>(
        &self,
        value: ConfirmSummary<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_action<'a>(
        &self,
        value: ConfirmAction<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn select_menu<'a>(
        &self,
        value: SelectMenu<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_properties<'a>(
        &self,
        value: ConfirmProperties<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_properties<'a>(
        &self,
        value: ShowProperties<'a>,
    ) -> FastResult<(), WireError>;
    extern "C" fn show_warning<'a>(&self, value: ShowWarning<'a>) -> FastResult<(), WireError>;
    extern "C" fn show_info_with_cancel<'a>(
        &self,
        value: ShowInfoWithCancel<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_mismatch<'a>(
        &self,
        value: ShowMismatch<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_trade<'a>(
        &self,
        value: ConfirmTrade<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_danger<'a>(
        &self,
        value: ShowDanger<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_success<'a>(&self, value: ShowSuccess<'a>) -> FastResult<(), WireError>;
    extern "C" fn request_number<'a>(
        &self,
        value: RequestNumber<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_public_key<'a>(
        &self,
        value: ShowPublicKey<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_with_info<'a>(
        &self,
        value: ConfirmWithInfo<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_address<'a>(
        &self,
        value: ShowAddress<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;

    extern "C" fn init_progress<'a>(
        &self,
        description: StabbyOption<Slice<'a, u8>>,
        title: StabbyOption<Slice<'a, u8>>,
        indeterminate: bool,
        danger: bool,
    ) -> FastResult<(), WireError>;
    extern "C" fn update_progress<'a>(
        &self,
        description: StabbyOption<Slice<'a, u8>>,
        value: u32,
    ) -> FastResult<(), WireError>;
    extern "C" fn end_progress(&self) -> FastResult<(), WireError>;
}

pub type UiV1Vtable = stabby::vtable!(UiV1 + Send + Sync);
pub type UiV1Ref<'a> = stabby::DynRef<'a, UiV1Vtable>;
pub type StaticUiV1 = UiV1Ref<'static>;
