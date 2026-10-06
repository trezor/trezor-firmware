//! Stable-ABI mirror of the UI requests `modui` sends, and of the reply.
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
//! issue. [`opt_bytes`]/[`as_opt_str`] convert at the edges.

use stabby::option::Option as StabbyOption;
use stabby::slice::Slice;
use stabby::str::Str;
use ufmt::derive::uDebug;

use super::util::FastResult;
use super::wire::WireError;

/// Build a layout, show it, and forget it. The handle is ignored.
pub const OP_ONCE: u16 = 0;
/// Build a layout and keep it alive under the handle.
pub const OP_OPEN: u16 = 1;
/// Show the layout already held under the handle, without rebuilding it.
pub const OP_REOPEN: u16 = 2;
/// Bits a handle may use; Core packs it with the op into one IPC message id.
pub const HANDLE_BITS: u16 = 12;

/// Converts an optional `&str` constructor argument into the
/// niche-friendly `StabbyOption<Slice<u8>>` field representation.
pub(crate) fn opt_bytes(s: Option<&str>) -> StabbyOption<Slice<'_, u8>> {
    s.map(|s| Slice::from(s.as_bytes())).into()
}

/// Recovers the `&str` an [`opt_bytes`]-produced field holds, if any.
///
/// # Safety
///
/// `bytes`, if present, must have come from [`opt_bytes`] applied to a
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
    pub key: Str<'a>,
    pub value: Str<'a>,
    pub mono: bool,
}

impl<'a> Property<'a> {
    pub fn new(key: &'a str, value: &'a str, mono: bool) -> Self {
        Self {
            key: key.into(),
            value: value.into(),
            mono,
        }
    }

    pub fn mono(key: &'a str, value: &'a str) -> Self {
        Self::new(key, value, true)
    }

    pub fn plain(key: &'a str, value: &'a str) -> Self {
        Self::new(key, value, false)
    }
}

/// Mirrors [`crate::structs::UiReply`]; see there for what each answer means.
#[must_use]
#[stabby::stabby]
#[repr(C, u8)]
#[derive(uDebug, Clone, Copy, PartialEq, Eq)]
pub enum UiReply {
    Confirmed,
    Cancelled,
    WantsMore,
    Choice(u16),
    Forward,
    Backward,
    ConfirmedAll,
}

/// Mirrors [`crate::structs::Severity`]; see there for what each one means.
#[stabby::stabby]
#[repr(u8)]
#[derive(uDebug, Clone, Copy, PartialEq, Eq)]
pub enum Severity {
    Success,
    Done,
    Info,
    Warning,
    Danger,
}

/// A menu of selectable string items.
#[stabby::stabby]
#[derive(Clone)]
pub struct SelectMenu<'a> {
    pub items: Slice<'a, Str<'a>>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
}

impl<'a> SelectMenu<'a> {
    pub fn new(items: &'a [Str<'a>], br_name: Option<&'a str>, br_code: i32) -> Self {
        Self {
            items: items.into(),
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmAction<'a> {
    pub title: Str<'a>,
    pub action: Str<'a>,
    pub description: StabbyOption<Slice<'a, u8>>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub hold: bool,
    pub verb: StabbyOption<Slice<'a, u8>>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
    pub external_menu: bool,
}

impl<'a> ConfirmAction<'a> {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        title: &'a str,
        action: &'a str,
        description: Option<&'a str>,
        subtitle: Option<&'a str>,
        hold: bool,
        verb: Option<&'a str>,
        br_name: Option<&'a str>,
        br_code: i32,
        external_menu: bool,
    ) -> Self {
        Self {
            title: title.into(),
            action: action.into(),
            description: opt_bytes(description),
            subtitle: opt_bytes(subtitle),
            hold,
            verb: opt_bytes(verb),
            br_name: opt_bytes(br_name),
            br_code,
            external_menu,
        }
    }
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
    pub external_menu: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
}

impl<'a> ConfirmSummary<'a> {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        title: &'a str,
        amount: Option<&'a str>,
        amount_label: Option<&'a str>,
        fee: &'a str,
        fee_label: &'a str,
        account_title: Option<&'a str>,
        account_items: Option<&'a [Property<'a>]>,
        extra_title: Option<&'a str>,
        extra_items: Option<&'a [Property<'a>]>,
        back_button: bool,
        external_menu: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            amount: opt_bytes(amount),
            amount_label: opt_bytes(amount_label),
            fee: fee.into(),
            fee_label: fee_label.into(),
            account_title: opt_bytes(account_title),
            account_items: account_items.map(Into::into).into(),
            extra_title: opt_bytes(extra_title),
            extra_items: extra_items.map(Into::into).into(),
            back_button,
            external_menu,
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
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
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
    pub external_menu: bool,
    pub footer_text: StabbyOption<Slice<'a, u8>>,
    pub footer_bold: bool,
}

impl<'a> ConfirmValue<'a> {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        title: &'a str,
        content: &'a str,
        description: Option<&'a str>,
        br_name: Option<&'a str>,
        br_code: i32,
        is_data: bool,
        verb: Option<&'a str>,
        subtitle: Option<&'a str>,
        info: bool,
        hold: bool,
        chunkify: bool,
        page_counter: bool,
        external_menu: bool,
        footer: Option<(&'a str, bool)>,
    ) -> Self {
        let (footer_text, footer_bold) = match footer {
            Some((text, bold)) => (opt_bytes(Some(text)), bold),
            None => (opt_bytes(None), false),
        };
        Self {
            title: title.into(),
            value: content.into(),
            description: opt_bytes(description),
            is_data,
            subtitle: opt_bytes(subtitle),
            verb: opt_bytes(verb),
            info,
            hold,
            chunkify,
            page_counter,
            br_name: opt_bytes(br_name),
            br_code,
            external_menu,
            footer_text,
            footer_bold,
        }
    }
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

impl<'a> ConfirmProperties<'a> {
    pub fn new(
        title: &'a str,
        props: &'a [Property<'a>],
        subtitle: Option<&'a str>,
        verb: Option<&'a str>,
        hold: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            props: props.into(),
            subtitle: opt_bytes(subtitle),
            verb: opt_bytes(verb),
            hold,
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
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

impl<'a> ShowProperties<'a> {
    pub fn new(
        title: &'a str,
        props: &'a [Property<'a>],
        subtitle: Option<&'a str>,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            props: props.into(),
            subtitle: opt_bytes(subtitle),
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
}

/// Mirrors [`crate::structs::ShowNotice`].
#[stabby::stabby]
#[derive(Clone)]
pub struct ShowNotice<'a> {
    pub severity: Severity,
    pub title: Str<'a>,
    pub content: Str<'a>,
    pub external_menu: bool,
    pub cancel: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
}

impl<'a> ShowNotice<'a> {
    pub fn new(
        severity: Severity,
        title: &'a str,
        content: &'a str,
        external_menu: bool,
        cancel: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            severity,
            title: title.into(),
            content: content.into(),
            external_menu,
            cancel,
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
}

/// Talks to Core's UI/progress screens — implemented in `core/embed/api`
/// against [`super::wire::WireV1`].
///
/// Each screen method sends one request and returns Core's reply. `op` is one
/// of [`OP_ONCE`], [`OP_OPEN`], [`OP_REOPEN`]; `handle` names the layout Core
/// keeps for the last two, until [`UiV1::close`].
#[stabby::stabby(checked)]
pub trait UiV1: Send + Sync {
    extern "C" fn confirm_action<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmAction<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn confirm_value<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmValue<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn confirm_summary<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmSummary<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn confirm_properties<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ConfirmProperties<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn show_properties<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ShowProperties<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn show_notice<'a>(
        &self,
        op: u16,
        handle: u16,
        value: ShowNotice<'a>,
    ) -> FastResult<UiReply, WireError>;
    extern "C" fn select_menu<'a>(
        &self,
        op: u16,
        handle: u16,
        value: SelectMenu<'a>,
    ) -> FastResult<UiReply, WireError>;
    /// Drops the layout held under `handle`. Shows nothing.
    extern "C" fn close(&self, handle: u16) -> FastResult<(), WireError>;

    extern "C" fn init_progress<'a>(
        &self,
        description: StabbyOption<Slice<'a, u8>>,
        title: StabbyOption<Slice<'a, u8>>,
        indeterminate: bool,
        danger: bool,
    ) -> FastResult<(), WireError>;
    /// `value` is how far along, from 0 to 1000.
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
